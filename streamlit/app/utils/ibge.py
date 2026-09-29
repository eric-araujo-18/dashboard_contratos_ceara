"""
População dos municípios (IBGE, Censo 2022).

Convertido do notebook data/api/ibge.ipynb para um módulo .py normal
(mesmo motivo do utils/pncp.py: o app.py precisa importar isto).
Se o JSON local ainda não existir, é baixado automaticamente na
primeira chamada de carregar_populacao().
"""
from __future__ import annotations

import json
import unicodedata

import pandas as pd
import requests

from utils.config import IBGE_DIR, POPULACAO_CSV, POPULACAO_JSON

URL_IBGE = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/4714/"
    "periodos/2022/variaveis/93?localidades=N6[N3[23]]"
)


def normalizar_nome(nome) -> str:
    nome = unicodedata.normalize("NFKD", " ".join(str(nome).strip().upper().split()))
    return "".join(c for c in nome if not unicodedata.combining(c))


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
                        "municipio": loc["nome"],
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
        return json.loads(POPULACAO_JSON.read_text(encoding="utf-8"))
    try:
        return baixar_populacao_ibge()
    except Exception:
        return {}


def populacao_por_codigo(populacao_por_nome: dict) -> dict:
    """
    Formato que o mapa_ceara.html espera: {codigo_ibge: {"populacao": n}}.
    Inclui também o código de 6 dígitos (sem dígito verificador), por segurança.
    """
    saida = {}
    for dados in populacao_por_nome.values():
        codigo = str(dados["codigo_ibge"])
        item = {"populacao": int(dados["populacao"])}
        saida[codigo] = item
        saida[codigo[:6]] = item
    return saida