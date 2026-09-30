"""
Download dos contratos do PNCP por intervalo de datas.

Convertido do notebook data/api/pncp.ipynb para um módulo .py normal:
notebooks (.ipynb) não podem ser importados pelo app.py sem ferramentas
extras, então a versão que o dashboard realmente usa vive aqui. O
notebook original fica como registro do desenvolvimento.

Por que é lento e o que foi feito
---------------------------------
O endpoint /v1/contratos NÃO tem filtro de UF (só dataInicial, dataFinal,
cnpjOrgao, codigoUnidadeAdministrativa e usuarioId). Então é preciso baixar
os contratos do Brasil inteiro e filtrar o Ceará aqui. Para acelerar:

1. Download dia a dia, em paralelo: cada dia é uma consulta separada, o
   que evita que publicações novas "empurrem" as páginas durante o download.
2. Filtro da UF página a página: não guarda em memória os contratos do
   resto do país, só os do Ceará.
3. Uma sessão HTTP por thread: reaproveita a conexão (keep-alive) sem
   compartilhar a mesma Session entre threads.
4. Nenhuma página é perdida em silêncio: o que falhar depois da segunda
   passada é devolvido para o app avisar.

Por que falhava e o que mudou (v2)
----------------------------------
- O firewall (WAF) do PNCP recusa clientes sem User-Agent de navegador.
  O requests manda "python-requests/x.y", então agora mandamos um
  User-Agent de navegador.
- O limite de requisições nem sempre vem como HTTP 429: às vezes o
  servidor responde 200 com uma página HTML. Antes isso virava um erro de
  JSON e uma tentativa perdida; agora é tratado como "vá mais devagar".
- 10 threads disparando ao mesmo tempo estouravam o limite do servidor.
  Agora há um controle de ritmo GLOBAL (todas as threads juntas): um
  intervalo mínimo entre requisições que dobra quando o servidor reclama
  e volta a diminuir aos poucos quando tudo corre bem. Um 429 pausa todas
  as threads, não só a que recebeu o erro.
- Mais tentativas, com espera exponencial (2, 4, 8, 16 s...) e jitter.
- Diagnóstico: o motivo de cada tentativa que falhou é contado e devolvido
  em info["motivos_falha"], para saber se o problema é tempo esgotado,
  limite do servidor, conexão derrubada etc.
"""
from __future__ import annotations

import random
import threading
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
import requests

from utils.config import CONTRATOS_DIR

BASE_URL = "https://pncp.gov.br/api/consulta/v1/contratos"

HEADERS = {
    "Accept": "application/json",
    # o WAF do PNCP barra clientes sem User-Agent de navegador
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    ),
}

TAMANHO_PAGINA = 500     # máximo aceito pelo endpoint /contratos
MAX_WORKERS = 4          # conexões simultâneas na 1ª passada
MAX_WORKERS_RETRY = 2    # conexões simultâneas na 2ª passada
TENTATIVAS = 5
TIMEOUT = (10, 60)       # (conectar, ler) em segundos
INTERVALO_MIN = 0.25     # intervalo mínimo entre requisições (≈ 4 por segundo no total)
INTERVALO_MAX = 3.0      # teto quando o servidor está reclamando
ESPERA_MAX = 60          # teto da espera entre tentativas
STATUS_TEMPORARIOS = {408, 429, 500, 502, 503, 504}  # vale a pena tentar de novo

Progresso = Callable[[float, str], None]


class ErroPNCP(RuntimeError):
    """Falha ao consultar o PNCP."""


# ---------------------------------------------------------------------------
# CONTROLE DE RITMO (compartilhado por todas as threads de um download)
# ---------------------------------------------------------------------------

class _Controle:
    """
    Distribui as requisições no tempo e reage ao servidor:
    - cada requisição espera sua "vez" (intervalo mínimo entre elas);
    - quando o servidor pede calma, todas as threads pausam e o intervalo dobra;
    - a cada sucesso o intervalo diminui um pouco, até voltar ao mínimo.
    Também conta os motivos das tentativas que falharam.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._proxima = 0.0
        self._pausa_ate = 0.0
        self._intervalo = INTERVALO_MIN
        self.motivos: Counter[str] = Counter()

    def aguardar_vez(self) -> None:
        with self._lock:
            agora = time.monotonic()
            vez = max(agora, self._proxima, self._pausa_ate)
            self._proxima = vez + self._intervalo
        if vez > agora:
            time.sleep(vez - agora)

    def desacelerar(self, pausa: float) -> None:
        with self._lock:
            self._pausa_ate = max(self._pausa_ate, time.monotonic() + pausa)
            self._intervalo = min(self._intervalo * 2, INTERVALO_MAX)

    def sucesso(self) -> None:
        with self._lock:
            self._intervalo = max(self._intervalo * 0.9, INTERVALO_MIN)

    def registrar(self, motivo: str) -> None:
        with self._lock:
            self.motivos[motivo] += 1


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

_local = threading.local()


def _sessao() -> requests.Session:
    """Uma Session por thread (reaproveita conexão sem compartilhar entre threads)."""
    sessao = getattr(_local, "sessao", None)
    if sessao is None:
        sessao = requests.Session()
        sessao.headers.update(HEADERS)
        _local.sessao = sessao
    return sessao


def _descartar_sessao() -> None:
    sessao = getattr(_local, "sessao", None)
    if sessao is not None:
        try:
            sessao.close()
        except Exception:
            pass
        _local.sessao = None


def _parece_json(resposta: requests.Response) -> bool:
    tipo = resposta.headers.get("Content-Type", "").lower()
    if "json" in tipo:
        return True
    return resposta.text.lstrip()[:1] in ("{", "[")


def _consultar_pagina(params: dict, controle: _Controle) -> Optional[dict]:
    """Retorna o JSON da página ou None se todas as tentativas falharem."""
    for tentativa in range(1, TENTATIVAS + 1):
        controle.aguardar_vez()
        espera = min(ESPERA_MAX, 2 ** tentativa)
        motivo = ""
        try:
            resposta = _sessao().get(BASE_URL, params=params, timeout=TIMEOUT)
            codigo = resposta.status_code

            if codigo == 204:  # sem conteúdo
                controle.sucesso()
                return {"data": [], "totalPaginas": 0}

            if codigo == 200:
                if _parece_json(resposta):
                    try:
                        dados = resposta.json()
                        controle.sucesso()
                        return dados
                    except ValueError:
                        motivo = "JSON incompleto/inválido"
                else:
                    # limite do servidor disfarçado de 200 com página HTML
                    motivo = "HTML no lugar de JSON (limite do servidor)"
                    controle.desacelerar(espera)

            elif codigo in STATUS_TEMPORARIOS:
                motivo = f"HTTP {codigo}"
                retry_after = resposta.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    espera = max(espera, min(int(retry_after), 120))
                if codigo in (429, 503):
                    controle.desacelerar(espera)

            else:
                # 400, 404, 422...: tentar de novo não resolve
                controle.registrar(f"HTTP {codigo} (erro permanente)")
                return None

        except requests.Timeout:
            motivo = "tempo esgotado"
            _descartar_sessao()
        except requests.ConnectionError:
            motivo = "conexão recusada/derrubada"
            _descartar_sessao()
            controle.desacelerar(espera)
        except (requests.RequestException, OSError) as erro:
            # OSError cobre erros de socket que escapam (ex.: WinError 10054)
            motivo = f"erro de rede ({type(erro).__name__})"
            _descartar_sessao()

        controle.registrar(motivo)
        if tentativa < TENTATIVAS:
            # o "jitter" evita que as threads tentem de novo no mesmo instante
            time.sleep(espera + random.uniform(0, 1))
    return None


# ---------------------------------------------------------------------------
# DOWNLOAD
# ---------------------------------------------------------------------------

def nome_arquivo(data_inicial: date, data_final: date, uf: str = "CE") -> str:
    return f"contratos_{uf.lower()}_{data_inicial:%Y%m%d}_{data_final:%Y%m%d}.csv"


def _da_uf(registro: dict, uf: str) -> bool:
    return (registro.get("unidadeOrgao") or {}).get("ufSigla") == uf


def baixar_contratos(
    data_inicial: date,
    data_final: date,
    uf: str = "CE",
    progresso: Optional[Progresso] = None,
) -> tuple[pd.DataFrame, list[str], dict]:
    """
    Baixa os contratos publicados no período, dia a dia, e devolve só os da UF.

    Retorna (DataFrame da UF, lista de páginas que falharam mesmo após a
    segunda tentativa no formato "AAAAMMDD/página", dict com diagnóstico:
    total_paginas, registros_brutos, registros_uf, motivos_falha).
    """
    if data_inicial > data_final:
        raise ValueError("A data inicial não pode ser maior que a data final.")

    def avisar(fracao: float, texto: str) -> None:
        if progresso:
            progresso(min(max(fracao, 0.0), 1.0), texto)

    dias = [data_inicial + timedelta(days=i) for i in range((data_final - data_inicial).days + 1)]
    controle = _Controle()

    avisar(0.0, "Consultando o PNCP...")

    # estado de cada dia
    estado = {
        dia: {"total": None, "feitas": 0, "brutos": 0, "uf": [], "falhas": []}
        for dia in dias
    }

    def params(dia: date, pagina: int) -> dict:
        texto = f"{dia:%Y%m%d}"
        return {"dataInicial": texto, "dataFinal": texto, "tamanhoPagina": TAMANHO_PAGINA, "pagina": pagina}

    def registrar(dia: date, resposta: dict, contar: bool = True) -> None:
        dados = resposta.get("data") or []
        info = estado[dia]
        info["brutos"] += len(dados)
        info["uf"].extend(r for r in dados if _da_uf(r, uf))
        if contar:
            info["feitas"] += 1

    def progresso_geral() -> None:
        conhecidas = sum(i["total"] or 1 for i in estado.values())
        feitas = sum(i["feitas"] for i in estado.values())
        dias_ok = sum(1 for i in estado.values() if i["total"] is not None and i["feitas"] >= i["total"])
        avisar(
            0.95 * feitas / max(conhecidas, 1),
            f"Dia {dias_ok} de {len(dias)} · página {feitas} de ~{conhecidas}",
        )

    def baixar(tarefas: list[tuple[date, int]], workers: int, retentativa: bool) -> None:
        """
        Baixa as páginas pedidas. Quando chega a 1ª página de um dia, as
        demais páginas daquele dia entram na mesma fila (sem esperar o fim).
        """
        with ThreadPoolExecutor(max_workers=workers) as pool:
            def enviar(dia: date, pagina: int):
                return pool.submit(_consultar_pagina, params(dia, pagina), controle)

            futuros = {enviar(dia, p): (dia, p) for dia, p in tarefas}

            while futuros:
                concluidos, _ = wait(futuros, return_when=FIRST_COMPLETED)
                for futuro in concluidos:
                    dia, pagina = futuros.pop(futuro)
                    try:
                        resposta = futuro.result()
                    except Exception as erro:  # nunca deixa uma thread derrubar o download
                        controle.registrar(f"erro inesperado ({type(erro).__name__})")
                        resposta = None
                    info = estado[dia]

                    if resposta is None:
                        info["falhas"].append(pagina)
                        if not retentativa:
                            info["feitas"] += 1
                        if pagina == 1 and info["total"] is None:
                            info["total"] = 1  # sem a 1ª página não dá para saber o total
                    else:
                        registrar(dia, resposta, contar=not retentativa)
                        if pagina == 1:
                            total = max(int(resposta.get("totalPaginas") or 1), 1)
                            info["total"] = total
                            for p in range(2, total + 1):
                                futuros[enviar(dia, p)] = (dia, p)

                    if retentativa:
                        avisar(0.96, f"Tentando de novo as páginas que falharam ({len(futuros)} na fila)...")
                    else:
                        progresso_geral()

    # --- 1) primeira página de cada dia; as demais entram na fila assim que o total é conhecido ---
    baixar([(dia, 1) for dia in dias], MAX_WORKERS, retentativa=False)

    # --- 2) segunda passada, com menos concorrência, só para o que falhou ---
    falhas = [(dia, p) for dia, info in estado.items() for p in info["falhas"]]
    if falhas:
        for info in estado.values():
            info["falhas"] = []
        time.sleep(5)  # dá um respiro ao servidor antes de insistir
        baixar(falhas, MAX_WORKERS_RETRY, retentativa=True)

    # --- 3) junta os dias ---
    registros_uf = [r for info in estado.values() for r in info["uf"]]
    registros_brutos = sum(info["brutos"] for info in estado.values())
    total_paginas = sum(info["total"] or 0 for info in estado.values())

    falhas_finais = [f"{dia:%Y%m%d}/{p}" for dia, info in estado.items() for p in info["falhas"]]
    motivos = dict(controle.motivos.most_common())

    if len(falhas_finais) == sum((i["total"] or 1) for i in estado.values()):
        principal = next(iter(motivos), "motivo desconhecido")
        raise ErroPNCP(
            f"Não foi possível consultar o PNCP agora ({principal}). Tente novamente em instantes."
        )

    df = pd.json_normalize(registros_uf) if registros_uf else pd.DataFrame()
    if "numeroControlePNCP" in df.columns:
        df = df.drop_duplicates(subset="numeroControlePNCP")
    df = df.reset_index(drop=True)

    avisar(1.0, "Concluído.")

    info = {
        "total_paginas": total_paginas,
        "registros_brutos": registros_brutos,
        "registros_uf": len(df),
        # quantas TENTATIVAS falharam por motivo (inclui as que deram certo depois)
        "motivos_falha": motivos,
    }
    return df, sorted(falhas_finais), info


def salvar_csv(df: pd.DataFrame, data_inicial: date, data_final: date, uf: str = "CE") -> Path:
    CONTRATOS_DIR.mkdir(parents=True, exist_ok=True)
    destino = CONTRATOS_DIR / nome_arquivo(data_inicial, data_final, uf)
    df.to_csv(destino, index=False, encoding="utf-8-sig")
    return destino


def listar_arquivos() -> list[Path]:
    """CSVs já baixados, do mais recente para o mais antigo."""
    if not CONTRATOS_DIR.exists():
        return []
    return sorted(
        CONTRATOS_DIR.glob("contratos_*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )