"""
População dos municípios (IBGE, Censo 2022).

Convertido do notebook data/api/ibge.ipynb para um módulo .py normal
(mesmo motivo do utils/pncp.py: o app.py precisa importar isto).
Se o JSON local ainda não existir, é baixado automaticamente na
primeira chamada de carregar_populacao().
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests

from utils.config import IBGE_DIR, POPULACAO_CSV, POPULACAO_JSON

URL_IBGE = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/4714/"
    "periodos/2022/variaveis/93?localidades=N6[N3[23]]"
)

# A API do IBGE devolve os nomes como "Crateús - CE"; o PNCP e o GeoJSON
# usam só "Crateús". Sem remover o sufixo, nenhum município casava.
_SUFIXO_UF = re.compile(r"\s*-\s*[A-Z]{2}$")


def normalizar_nome(nome) -> str:
    nome = " ".join(str(nome).strip().upper().split())
    nome = _SUFIXO_UF.sub("", nome)
    nome = unicodedata.normalize("NFKD", nome)
    return "".join(c for c in nome if not unicodedata.combining(c))


def _nome_sem_uf(nome: str) -> str:
    return re.sub(r"\s*-\s*[A-Za-z]{2}$", "", str(nome).strip())


def baixar_populacao_ibge() -> dict:
    resposta = requests.get(URL_IBGE, timeout=60)
    resposta.raise_for_status()

    registros = []
    for variavel in resposta.json():
        for resultado in variavel.get("resultados", []):
            for serie in resultado.get("series", []):
                loc = serie.get("localidade", {})
                valor = serie.get("serie", {}).get("2022")
                if not loc.get("nome") or valor in (None, "", "-", "...", ".."):
                    continue
                registros.append(
                    {
                        "codigo_ibge": str(loc.get("id")),
                        "municipio": _nome_sem_uf(loc["nome"]),
                        "municipio_normalizado": normalizar_nome(loc["nome"]),
                        "populacao": int(float(valor)),
                    }
                )

    df = pd.DataFrame(registros).sort_values("municipio").reset_index(drop=True)
    por_nome = {
        r["municipio_normalizado"]: {
            "codigo_ibge": r["codigo_ibge"],
            "municipio": r["municipio"],
            "populacao": r["populacao"],
        }
        for r in registros
    }

    IBGE_DIR.mkdir(parents=True, exist_ok=True)
    POPULACAO_JSON.write_text(json.dumps(por_nome, ensure_ascii=False, indent=2), encoding="utf-8")
    df.to_csv(POPULACAO_CSV, index=False, encoding="utf-8-sig")
    return por_nome


def carregar_populacao() -> dict:
    """{NOME NORMALIZADO: {codigo_ibge, municipio, populacao}}. Vazio se indisponível."""
    if POPULACAO_JSON.exists():
        bruto = json.loads(POPULACAO_JSON.read_text(encoding="utf-8"))
    else:
        try:
            bruto = baixar_populacao_ibge()
        except Exception:
            return {}

    # re-normaliza as chaves: o JSON salvo por versões antigas tinha
    # chaves como "CRATEUS - CE", que não casavam com os contratos
    return {
        normalizar_nome(dados.get("municipio", chave)): {
            **dados,
            "municipio": _nome_sem_uf(dados.get("municipio", chave)),
        }
        for chave, dados in bruto.items()
    }


# ---------------------------------------------------------------------------
# PIB DOS MUNICÍPIOS
# ---------------------------------------------------------------------------

# Tabela 5938 do SIDRA (PIB dos Municípios), variável 37: PIB a preços
# correntes, em MIL reais. O ano não é fixo: usa sempre o mais recente que o
# IBGE publicou (o PIB municipal sai com cerca de dois anos de atraso, então
# não existe PIB do mesmo ano dos contratos). Cada ano baixado fica salvo em
# ibge_csv/pib_ceara_ibge_<ano>.csv e serve de reserva sem internet.
URL_PIB_PERIODOS = "https://servicodados.ibge.gov.br/api/v3/agregados/5938/periodos"
URL_PIB = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/5938/"
    "periodos/{ano}/variaveis/37?localidades=N6[N3[23]]"
)
# o mapa é redesenhado a cada clique: a pergunta "saiu ano novo?" vai ao IBGE
# no máximo uma vez por dia (ou a cada 10 minutos, se a última falhou)
VALIDADE_CONSULTA = 24 * 3600
VALIDADE_FALHA = 10 * 60
_PIB_ATUAL = {"quando": 0.0, "validade": 0.0, "ano": None, "pib": {}}


def _csv_pib(ano: str) -> Path:
    return IBGE_DIR / f"pib_ceara_ibge_{ano}.csv"


def ultimo_ano_pib() -> str:
    """Ano mais recente do PIB dos Municípios publicado pelo IBGE (ex.: "2023")."""
    resposta = requests.get(URL_PIB_PERIODOS, timeout=10)
    resposta.raise_for_status()
    return max(str(periodo["id"]) for periodo in resposta.json())


def _ano_local_mais_recente() -> str | None:
    """Ano do arquivo de PIB mais novo já salvo (reserva sem internet)."""
    anos = sorted(arquivo.stem.rsplit("_", 1)[-1] for arquivo in IBGE_DIR.glob("pib_ceara_ibge_*.csv"))
    return anos[-1] if anos else None


def baixar_pib_ibge(ano: str) -> pd.DataFrame:
    """Baixa o PIB de cada município do Ceará no ano pedido e salva o CSV (valor em reais)."""
    resposta = requests.get(URL_PIB.format(ano=ano), timeout=60)
    resposta.raise_for_status()

    registros = []
    for variavel in resposta.json():
        for resultado in variavel.get("resultados", []):
            for serie in resultado.get("series", []):
                loc = serie.get("localidade", {})
                valor = serie.get("serie", {}).get(ano)
                if not loc.get("id") or valor in (None, "", "-", "...", ".."):
                    continue
                registros.append(
                    {
                        "codigo_ibge": str(loc["id"]),
                        "municipio": _nome_sem_uf(loc.get("nome", "")),
                        "pib": float(valor) * 1000,  # a API devolve em mil reais
                    }
                )

    df = pd.DataFrame(registros).sort_values("municipio").reset_index(drop=True)
    IBGE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(_csv_pib(ano), index=False, encoding="utf-8-sig")
    return df


def _pib_atual() -> dict:
    """
    {"ano", "pib"} do ano mais recente disponível. Pergunta ao IBGE qual é o
    último ano; se ainda não tiver o arquivo dele, baixa. Sem internet, usa o
    arquivo mais novo já salvo. O resultado fica guardado por VALIDADE_CONSULTA.
    """
    agora = time.time()
    if agora - _PIB_ATUAL["quando"] < _PIB_ATUAL["validade"]:
        return _PIB_ATUAL

    try:
        ano = ultimo_ano_pib()
    except Exception:
        ano = _ano_local_mais_recente()

    df = None
    if ano is not None:
        try:
            df = pd.read_csv(_csv_pib(ano), dtype={"codigo_ibge": str}) if _csv_pib(ano).exists() else baixar_pib_ibge(ano)
        except Exception:
            # o download do ano novo falhou: fica com o mais novo salvo
            ano = _ano_local_mais_recente()
            df = pd.read_csv(_csv_pib(ano), dtype={"codigo_ibge": str}) if ano else None

    if df is None:
        _PIB_ATUAL.update(quando=agora, validade=VALIDADE_FALHA, ano=None, pib={})
    else:
        pib = dict(zip(df["codigo_ibge"].astype(str), df["pib"].astype(float)))
        _PIB_ATUAL.update(quando=agora, validade=VALIDADE_CONSULTA, ano=ano, pib=pib)
    return _PIB_ATUAL


def carregar_pib() -> dict:
    """{codigo_ibge (7 dígitos): PIB em reais} do ano mais recente; vazio se indisponível."""
    return _pib_atual()["pib"]


def ano_pib() -> str | None:
    """Ano do PIB usado por carregar_pib() (ex.: "2023")."""
    return _pib_atual()["ano"]


def populacao_por_codigo(
    populacao_por_nome: dict, pib_por_codigo: dict | None = None, ano_pib: str | None = None
) -> dict:
    """
    Formato que o mapa_ceara.html espera:
    {codigo_ibge: {"populacao": n, "pib": x, "pibAno": "2023"}}.
    O PIB (em reais) só entra quando informado (carregar_pib). Inclui também
    o código de 6 dígitos (sem dígito verificador), por segurança.
    """
    pib_por_codigo = pib_por_codigo or {}
    saida = {}
    for dados in populacao_por_nome.values():
        codigo = str(dados["codigo_ibge"])
        item = {"populacao": int(dados["populacao"])}
        if codigo in pib_por_codigo:
            item["pib"] = float(pib_por_codigo[codigo])
            item["pibAno"] = ano_pib
        saida[codigo] = item
        saida[codigo[:6]] = item
    return saida