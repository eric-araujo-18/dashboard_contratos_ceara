"""
Download dos contratos do PNCP por intervalo de datas.

Convertido do notebook data/api/pncp.ipynb para um módulo .py normal:
notebooks (.ipynb) não podem ser importados pelo app.py sem ferramentas
extras, então a versão que o dashboard realmente usa vive aqui. O
notebook original fica como registro do desenvolvimento.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
import requests

from utils.config import CONTRATOS_DIR

BASE_URL = "https://pncp.gov.br/api/consulta/v1/contratos"
TAMANHO_PAGINA = 500
MAX_WORKERS = 4
MAX_WORKERS_RETRY = 2
STAGGER_SEGUNDOS = 0.15  # pequena pausa entre disparos, para não rajar o servidor
TENTATIVAS = 3
TIMEOUT = 45

Progresso = Callable[[float, str], None]


class ErroPNCP(RuntimeError):
    """Falha ao consultar o PNCP."""


def _consultar_pagina(params: dict) -> Optional[dict]:
    """
    Retorna o JSON da página ou None se todas as tentativas falharem.

    Propositalmente NÃO reaproveita uma requests.Session() entre as
    threads do ThreadPoolExecutor: uma Session compartilhada sob 10
    threads simultâneas pode falhar silenciosamente sob certas redes
    (mais comum no Windows), fazendo várias páginas serem descartadas
    sem aviso. Uma requisição nova por chamada é o mesmo padrão do
    notebook original, que já se mostrou confiável.
    """
    for tentativa in range(1, TENTATIVAS + 1):
        time.sleep(STAGGER_SEGUNDOS)  # espaça as requisições, mesmo com poucas threads
        try:
            resposta = requests.get(BASE_URL, params=params, timeout=TIMEOUT)
            if resposta.status_code == 200:
                return resposta.json()
            if resposta.status_code == 204:  # sem conteúdo
                return {"data": [], "totalPaginas": 0}
        except (requests.RequestException, ValueError, OSError):
            # OSError cobre erros de socket que às vezes escapam sem
            # virar requests.RequestException (ex.: ConnectionResetError
            # / WinError 10054 no Windows) — sem isso, a exceção sobe e
            # derruba a thread inteira em vez de só marcar a página
            # como falha para a segunda passada tentar de novo.
            pass
        time.sleep(tentativa * 2)  # recuo maior entre tentativas: 2s, 4s, 6s
    return None


def nome_arquivo(data_inicial: date, data_final: date, uf: str = "CE") -> str:
    return f"contratos_{uf.lower()}_{data_inicial:%Y%m%d}_{data_final:%Y%m%d}.csv"


def baixar_contratos(
    data_inicial: date,
    data_final: date,
    uf: str = "CE",
    progresso: Optional[Progresso] = None,
) -> tuple[pd.DataFrame, list[int], dict]:
    """
    Baixa todas as páginas do período (sem filtro de UF na API — o
    endpoint /contratos não tem esse parâmetro) e filtra pela UF depois,
    em memória, igual ao notebook original.

    Retorna (DataFrame já filtrado por uf, páginas que falharam mesmo
    após a segunda tentativa, dict com diagnóstico: total_paginas,
    registros_brutos, registros_uf).
    """
    if data_inicial > data_final:
        raise ValueError("A data inicial não pode ser maior que a data final.")

    def avisar(fracao: float, texto: str) -> None:
        if progresso:
            progresso(fracao, texto)

    params_base = {
        "dataInicial": f"{data_inicial:%Y%m%d}",
        "dataFinal": f"{data_final:%Y%m%d}",
        "tamanhoPagina": TAMANHO_PAGINA,
    }

    avisar(0.5, "Consultando o PNCP...")

    primeira = _consultar_pagina({**params_base, "pagina": 1})
    if primeira is None:
        raise ErroPNCP(
            "Não foi possível consultar o PNCP agora. Tente novamente em instantes."
        )

    total = int(primeira.get("totalPaginas") or 1)
    registros = list(primeira.get("data") or [])
    avisar(1 / total if total else 1.0, f"Baixando página 1 de {total}")

    falhas: list[int] = []

    if total > 1:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futuros = {
                pool.submit(_consultar_pagina, {**params_base, "pagina": p}): p
                for p in range(2, total + 1)
            }
            for concluidas, futuro in enumerate(as_completed(futuros), start=2):
                resposta = futuro.result()
                if resposta is None:
                    falhas.append(futuros[futuro])
                else:
                    registros.extend(resposta.get("data") or [])
                avisar(concluidas / total, f"Baixando página {concluidas} de {total}")

        # segunda passada, sequencial (sem concorrência), só para as
        # páginas que falharam sob carga — costuma recuperar a maioria.
        if falhas:
            n_falhas = len(falhas)
            ainda_falhando: list[int] = []
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_RETRY) as pool_retry:
                futuros_retry = {
                    pool_retry.submit(_consultar_pagina, {**params_base, "pagina": p}): p
                    for p in falhas
                }
                for concluidas_retry, futuro in enumerate(as_completed(futuros_retry), start=1):
                    pagina = futuros_retry[futuro]
                    resposta = futuro.result()
                    if resposta is None:
                        ainda_falhando.append(pagina)
                    else:
                        registros.extend(resposta.get("data") or [])
                    avisar(
                        0.97,
                        f"Tentando de novo: {concluidas_retry} de {n_falhas} página(s) pendente(s)...",
                    )
            falhas = ainda_falhando

    df = pd.json_normalize(registros)
    registros_brutos = len(df)

    if "unidadeOrgao.ufSigla" in df.columns:
        df = df[df["unidadeOrgao.ufSigla"] == uf]
    if "numeroControlePNCP" in df.columns:
        df = df.drop_duplicates(subset="numeroControlePNCP")

    df = df.reset_index(drop=True)

    avisar(1.0, "Concluído.")

    info = {
        "total_paginas": total,
        "registros_brutos": registros_brutos,
        "registros_uf": len(df),
    }
    return df, sorted(falhas), info


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