"""
Tratamento dos dados brutos do PNCP.

Convertido do notebook notebooks/tratamento.ipynb para um módulo .py
normal (mesmo motivo dos demais: o app.py precisa importar isto).

Colunas: ficam só as usadas pela detecção de anomalias ou pelo painel
(COLUNAS_MANTER). As que o projeto usa com outro nome são RENOMEADAS (e
não copiadas), e nenhuma coluna nova é criada quando a informação já existe:
o ano de publicação, por exemplo, é tirado da própria data na hora de
filtrar (pipeline.ano_publicacao).
"""
from __future__ import annotations

import unicodedata

import pandas as pd

# Colunas do PNCP que a análise usa: nome no PNCP -> nome no projeto.
# É uma lista do que MANTER (e não do que descartar) porque o conjunto de
# colunas muda entre downloads: campos compostos, como os de sub-rogação,
# só aparecem quando algum contrato do período os preenche, e o PNCP inclui
# campos novos com o tempo (ex.: frutoAdesao, emendaParlamentar). Qualquer
# coluna fora desta lista é descartada, e a base tratada tem sempre as 15.
COLUNAS_MANTER = {
    "numeroControlePNCP": "numeroControlePNCP",        # identificador único
    "valorGlobal": "valor",
    "objetoContrato": "objeto",
    "categoriaProcesso.id": "categoriaProcesso.id",    # recategorização e alienações
    "tipoContrato.nome": "tipoContrato.nome",          # contrato x empenho
    "orgaoEntidade.esferaId": "esfera",                # os códigos viram nomes logo abaixo
    "orgaoEntidade.cnpj": "orgaoEntidade.cnpj",        # concentração e recorrência
    "niFornecedor": "niFornecedor",                    # concentração e recorrência
    "nomeRazaoSocialFornecedor": "fornecedor",
    "unidadeOrgao.municipioNome": "municipio",
    "unidadeOrgao.codigoIbge": "codigoIbge",           # chave para IBGE e mapa
    "dataPublicacaoPncp": "dataPublicacaoPncp",        # ano do filtro e alertas
    "dataAssinatura": "dataAssinatura",                # alerta de assinatura após publicação
    "dataVigenciaInicio": "dataVigenciaInicio",        # duração (vigência)
    "dataVigenciaFim": "dataVigenciaFim",              # duração (vigência)
}

COLUNAS_DATA = ["dataAssinatura", "dataVigenciaInicio", "dataVigenciaFim", "dataPublicacaoPncp"]

# esferaId do PNCP -> nome legível
ESFERAS = {"M": "Municipal", "E": "Estadual", "F": "Federal", "D": "Distrital", "N": "Não se aplica"}


def padronizar_texto(texto):
    if pd.isna(texto):
        return texto
    texto = " ".join(str(texto).strip().upper().split())
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def _serie(df: pd.DataFrame, coluna: str, padrao="") -> pd.Series:
    return df[coluna] if coluna in df.columns else pd.Series(padrao, index=df.index)


def _documento(valor, tipo_pessoa: str) -> str | None:
    """
    CNPJ/CPF como texto, com os zeros à esquerda. Ao ler o CSV, o pandas
    transforma o documento em número e "07954480000179" vira 7954480000179.
    PJ (e órgão público) = CNPJ, 14 dígitos; PF = CPF, 11 dígitos (alguns PF
    vêm com 14). Documento estrangeiro (PE) ou com letras fica como está.
    """
    if pd.isna(valor):
        return None
    texto = str(valor).strip().removesuffix(".0")
    if not texto.isdigit():
        return texto
    if tipo_pessoa == "PJ" or len(texto) > 11:
        return texto.zfill(14)
    if tipo_pessoa == "PF":
        return texto.zfill(11)
    return texto


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

    # identificadores como texto, com zeros à esquerda (antes da seleção,
    # porque o tipoPessoa, que diz se é CPF ou CNPJ, é descartado nela)
    if "orgaoEntidade.cnpj" in df.columns:
        df["orgaoEntidade.cnpj"] = df["orgaoEntidade.cnpj"].map(lambda v: _documento(v, "PJ"))
    if "niFornecedor" in df.columns:
        tipo = _serie(df, "tipoPessoa", None)
        df["niFornecedor"] = [_documento(v, t) for v, t in zip(df["niFornecedor"], tipo)]

    # seleção de atributos: só as colunas da lista, já com os nomes do projeto
    df = df[[c for c in COLUNAS_MANTER if c in df.columns]].rename(columns=COLUNAS_MANTER)

    # valor: numérico e > 0
    df["valor"] = pd.to_numeric(_serie(df, "valor", None), errors="coerce").astype(float)
    antes = len(df)
    df = df[df["valor"].notna() & (df["valor"] > 0)]
    log["valor_invalido_removidos"] = antes - len(df)

    for coluna in COLUNAS_DATA:
        if coluna in df.columns:
            df[coluna] = pd.to_datetime(df[coluna], format="ISO8601", errors="coerce")

    # colunas de trabalho: só preenche vazios e acerta o tipo
    df["municipio"] = _serie(df, "municipio", "Não informado").fillna("Não informado").astype(str).str.strip()
    df["objeto"] = _serie(df, "objeto").fillna("").astype(str)
    df["fornecedor"] = _serie(df, "fornecedor", "Não informado").fillna("Não informado")

    # código IBGE do município (7 dígitos) — chave mais confiável que o nome
    # para cruzar com a população do IBGE e com o GeoJSON (ex.: Itapajé/Itapagé)
    codigo = pd.to_numeric(_serie(df, "codigoIbge", None), errors="coerce")
    df["codigoIbge"] = codigo.map(lambda v: str(int(v)) if pd.notna(v) else None)

    # esfera: os códigos do PNCP ("M", "E"...) viram nomes legíveis
    df["esfera"] = _serie(df, "esfera", None).map(ESFERAS).fillna("Não informada")

    df = df.sort_values("municipio", kind="stable").reset_index(drop=True)
    log["linhas_finais"] = len(df)
    return df, log
