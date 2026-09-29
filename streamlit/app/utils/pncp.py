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
3. Uma sessão HTTP por thread: reaproveita a conexão (keep-alive) em vez
   de abrir uma conexão TLS nova a cada página, sem compartilhar a mesma
   Session entre threads (o que causava falhas silenciosas no Windows).
4. Pausa só entre tentativas que falharam, não antes de toda requisição,
   respeitando o "Retry-After" do servidor e sem repetir erros permanentes.
5. Nenhuma página é perdida em silêncio: o que falhar depois da segunda
   passada é devolvido para o app avisar (o notebook original trocava a
   página por uma lista vazia sem avisar).
"""
from __future__ import annotations

import random
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
import requests

from utils.config import CONTRATOS_DIR

BASE_URL = "https://pncp.gov.br/api/consulta/v1/contratos"

TAMANHO_PAGINA = 500   # máximo aceito pelo endpoint /contratos
MAX_WORKERS = 10       # mesmo valor do notebook, que já funcionava bem; se falhar muito, reduza
MAX_WORKERS_RETRY = 3
TENTATIVAS = 3
TIMEOUT = 45
STATUS_TEMPORARIOS = {429, 500, 502, 503, 504}  # vale a pena tentar de novo

Progresso = Callable[[float, str], None]


class ErroPNCP(RuntimeError):
    """Falha ao consultar o PNCP."""


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

_local = threading.local()


def _sessao() -> requests.Session:
    """Uma Session por thread (reaproveita conexão sem compartilhar entre threads)."""
    sessao = getattr(_local, "sessao", None)
    if sessao is None:
        sessao = requests.Session()
        sessao.headers.update({"Accept": "application/json"})
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


def _consultar_pagina(params: dict) -> Optional[dict]:
    """Retorna o JSON da página ou None se todas as tentativas falharem."""
    for tentativa in range(1, TENTATIVAS + 1):
        espera = tentativa * 2
        try:
            resposta = _sessao().get(BASE_URL, params=params, timeout=TIMEOUT)
            if resposta.status_code == 200:
                return resposta.json()
            if resposta.status_code == 204:  # sem conteúdo
                return {"data": [], "totalPaginas": 0}
            if resposta.status_code not in STATUS_TEMPORARIOS:
                return None  # 400, 404...: tentar de novo não resolve
            # 429 = "muitas requisições": respeita o tempo pedido pelo servidor
            retry_after = resposta.headers.get("Retry-After", "")
            if retry_after.isdigit():
                espera = max(espera, int(retry_after))
        except (requests.RequestException, ValueError, OSError):
            # OSError cobre erros de socket que às vezes escapam sem virar
            # requests.RequestException (ex.: WinError 10054 no Windows).
            # Descarta a sessão para a próxima tentativa abrir uma conexão nova.
            _descartar_sessao()
        if tentativa < TENTATIVAS:
            # o "jitter" evita que as 10 threads tentem de novo no mesmo instante
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
    total_paginas, registros_brutos, registros_uf).
    """
    if data_inicial > data_final:
        raise ValueError("A data inicial não pode ser maior que a data final.")

    def avisar(fracao: float, texto: str) -> None:
        if progresso:
            progresso(min(max(fracao, 0.0), 1.0), texto)

    dias = [data_inicial + timedelta(days=i) for i in range((data_final - data_inicial).days + 1)]

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
            futuros = {pool.submit(_consultar_pagina, params(dia, p)): (dia, p) for dia, p in tarefas}

            while futuros:
                concluidos, _ = wait(futuros, return_when=FIRST_COMPLETED)
                for futuro in concluidos:
                    dia, pagina = futuros.pop(futuro)
                    resposta = futuro.result()
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
                                futuros[pool.submit(_consultar_pagina, params(dia, p))] = (dia, p)

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
        baixar(falhas, MAX_WORKERS_RETRY, retentativa=True)

    # --- 3) junta os dias ---
    registros_uf = [r for info in estado.values() for r in info["uf"]]
    registros_brutos = sum(info["brutos"] for info in estado.values())
    total_paginas = sum(info["total"] or 0 for info in estado.values())

    falhas_finais = [f"{dia:%Y%m%d}/{p}" for dia, info in estado.items() for p in info["falhas"]]

    if len(falhas_finais) == sum((i["total"] or 1) for i in estado.values()):
        raise ErroPNCP("Não foi possível consultar o PNCP agora. Tente novamente em instantes.")

    df = pd.json_normalize(registros_uf) if registros_uf else pd.DataFrame()
    if "numeroControlePNCP" in df.columns:
        df = df.drop_duplicates(subset="numeroControlePNCP")
    df = df.reset_index(drop=True)

    avisar(1.0, "Concluído.")

    info = {
        "total_paginas": total_paginas,
        "registros_brutos": registros_brutos,
        "registros_uf": len(df),
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