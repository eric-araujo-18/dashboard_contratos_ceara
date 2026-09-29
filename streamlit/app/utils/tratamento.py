"""
Tratamento dos dados brutos do PNCP.

Convertido do notebook notebooks/tratamento.ipynb para um módulo .py
normal (mesmo motivo dos demais: o app.py precisa importar isto).
"""
from __future__ import annotations

import unicodedata

import pandas as pd

COL_MUNICIPIO = "unidadeOrgao.municipioNome"

COLUNAS_DESCARTAR = [
    "urlCipi", "identificadorCipi",
    "orgaoSubRogado", "unidadeSubRogada",
    "orgaoSubRogado.cnpj", "orgaoSubRogado.razaoSocial",
    "orgaoSubRogado.esferaId", "orgaoSubRogado.poderId",
    "unidadeSubRogada.codigoUnidade", "unidadeSubRogada.ufSigla",
    "unidadeSubRogada.municipioNome", "unidadeSubRogada.nomeUnidade",
    "unidadeSubRogada.codigoIbge", "unidadeSubRogada.ufNome",
    "niFornecedorSubContratado", "nomeFornecedorSubContratado",
    "tipoPessoaSubContratada", "informacaoComplementar",
    "valorAcumulado", "processo",
]

COLUNAS_DATA = ["dataAssinatura", "dataVigenciaInicio", "dataVigenciaFim"]


def padronizar_texto(texto):
    if pd.isna(texto):
        return texto
    texto = " ".join(str(texto).strip().upper().split())
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def _serie(df: pd.DataFrame, coluna: str, padrao="") -> pd.Series:
    return df[coluna] if coluna in df.columns else pd.Series(padrao, index=df.index)


def tratar_contratos(df_bruto: pd.DataFrame, uf: str = "CE") -> tuple[pd.DataFrame, dict]:
    """Limpa o CSV bruto. Retorna (DataFrame tratado, log com contagens)."""
    df = df_bruto.copy()
    log = {"linhas_brutas": len(df)}

    if "unidadeOrgao.ufSigla" in df.columns:
        df = df[df["unidadeOrgao.ufSigla"] == uf]

    if "numeroControlePNCP" in df.columns:
        antes = len(df)
        df = df.drop_duplicates(subset="numeroControlePNCP")
        log["duplicados_removidos"] = antes - len(df)

    # país do fornecedor: preenche apenas quando vazio
    df["codigoPaisFornecedor"] = _serie(df, "codigoPaisFornecedor", None)
    df["codigoPaisFornecedor"] = df["codigoPaisFornecedor"].fillna("BRA")

    df = df.drop(columns=COLUNAS_DESCARTAR, errors="ignore")

    # valor: numérico e > 0
    df["valorGlobal"] = pd.to_numeric(df.get("valorGlobal"), errors="coerce")
    antes = len(df)
    df = df[df["valorGlobal"].notna() & (df["valorGlobal"] > 0)]
    log["valor_invalido_removidos"] = antes - len(df)

    for coluna in COLUNAS_DATA:
        if coluna in df.columns:
            df[coluna] = pd.to_datetime(df[coluna], errors="coerce")

    # colunas de trabalho, com nomes curtos
    df["municipio"] = _serie(df, COL_MUNICIPIO, "Não informado").fillna("Não informado").astype(str).str.strip()
    df["municipioNorm"] = df["municipio"].map(padronizar_texto)
    df["objeto"] = _serie(df, "objetoContrato").fillna("").astype(str)
    df["fornecedor"] = _serie(df, "nomeRazaoSocialFornecedor", "Não informado").fillna("Não informado")
    df["valor"] = df["valorGlobal"].astype(float)

    ano = pd.to_numeric(_serie(df, "anoContrato", None), errors="coerce")
    if "dataAssinatura" in df.columns:
        ano = ano.fillna(df["dataAssinatura"].dt.year)
    df["ano"] = ano.map(lambda v: str(int(v)) if pd.notna(v) else "N/D")

    df = df.sort_values("municipio", kind="stable").reset_index(drop=True)
    log["linhas_finais"] = len(df)
    return df, log