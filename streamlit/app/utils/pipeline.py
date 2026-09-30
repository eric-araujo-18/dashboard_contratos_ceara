"""
Orquestra o pipeline completo: tratamento -> classificação (regras + ML)
-> população (IBGE) -> detecção de anomalias (Isolation Forest) ->
agregados prontos para o dashboard (KPIs, mapa, categorias, ranking de risco).

É este módulo que o botão "Fazer análise" do app.py chama.
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np
import pandas as pd

from utils.anomalias import ATRIBUTOS_ROTULO, detectar_anomalias
from utils.classificador import classificar_por_regras, refinar_outros_com_ml
from utils.ibge import carregar_populacao, populacao_por_codigo
from utils.mapa import carregar_geojson
from utils.tratamento import padronizar_texto, tratar_contratos

Progresso = Callable[[float, str], None]

# "valor" e "valor_habitante" são o mesmo conceito (o segundo é usado nos
# municipais), então aparecem juntos no gráfico geral de fatores
ROTULO_FATOR = {
    "valor": "Valor acima do padrão da categoria",
    "valor_habitante": "Valor acima do padrão da categoria",
    "vigencia": ATRIBUTOS_ROTULO["vigencia"],
    "concentracao": ATRIBUTOS_ROTULO["concentracao"],
    "recorrencia": ATRIBUTOS_ROTULO["recorrencia"],
}
COLUNAS_SHAP = [f"shap_{a}" for a in ATRIBUTOS_ROTULO]
COLUNAS_DESVIO = [f"desvio_{a}" for a in ATRIBUTOS_ROTULO]


def fatias_shap(linha: pd.Series) -> list[tuple[str, float]]:
    """[(rótulo, % da contribuição)] das contribuições SHAP positivas de um contrato."""
    positivos: dict[str, float] = {}
    for c in COLUNAS_SHAP:
        atributo = c.removeprefix("shap_")
        desvio = linha.get(f"desvio_{atributo}", 1.0)
        # só conta o atributo que está de fato acima do padrão (mesma regra do motivo)
        if pd.notna(linha.get(c)) and linha[c] > 0 and pd.notna(desvio) and desvio > 0:
            rotulo = ROTULO_FATOR[atributo]
            positivos[rotulo] = positivos.get(rotulo, 0.0) + float(linha[c])
    total = sum(positivos.values())
    if total <= 0:
        return []
    return sorted(((r, v / total * 100) for r, v in positivos.items()), key=lambda kv: -kv[1])


def fatores_globais(df: pd.DataFrame) -> list[tuple[str, float]]:
    """Peso médio de cada fator (SHAP) entre os contratos de risco Alto."""
    if df.empty or "risco" not in df.columns:
        return []
    altos = df[df["risco"] == "Alto"]
    colunas = [c for c in COLUNAS_SHAP if c in altos.columns]
    if altos.empty or not colunas:
        return []
    positivos = altos[colunas].clip(lower=0).fillna(0)
    for c in colunas:  # mesma regra do motivo: só atributos acima do padrão
        desvio = f"desvio_{c.removeprefix('shap_')}"
        if desvio in altos.columns:
            positivos[c] = positivos[c].where(altos[desvio].fillna(0) > 0, 0.0)
    total = positivos.sum(axis=1).replace(0, np.nan)
    fatias = positivos.div(total, axis=0).mean() * 100
    fatias.index = [ROTULO_FATOR[c.removeprefix("shap_")] for c in fatias.index]
    fatias = fatias.groupby(level=0).sum().sort_values(ascending=False)
    return [(nome, round(float(v), 1)) for nome, v in fatias.items() if v > 0]


def _mapa_nome_geojson() -> dict:
    """{nome município normalizado: nome oficial exatamente como está no GeoJSON}."""
    geojson = carregar_geojson()
    return {
        padronizar_texto(feature["properties"]["name"]): feature["properties"]["name"]
        for feature in geojson["features"]
    }


def _mapa_codigo_geojson() -> dict:
    """{código IBGE (7 dígitos): nome oficial como está no GeoJSON}."""
    geojson = carregar_geojson()
    return {
        str(feature["properties"]["id"]): feature["properties"]["name"]
        for feature in geojson["features"]
    }


def _nome_geojson(df: pd.DataFrame) -> pd.Series:
    """
    Nome do município no GeoJSON para cada contrato. Casa primeiro pelo
    código IBGE (robusto a grafias diferentes, ex.: Itapajé x Itapagé)
    e usa o nome normalizado só como reserva.
    """
    por_nome = df["municipioNorm"].map(_mapa_nome_geojson())
    if "codigoIbge" not in df.columns:
        return por_nome
    return df["codigoIbge"].map(_mapa_codigo_geojson()).fillna(por_nome)


def _populacao(df: pd.DataFrame, pop_por_nome: dict) -> pd.Series:
    """População do município de cada contrato: pelo código IBGE, com o nome como reserva."""
    por_nome = df["municipioNorm"].map(lambda nome: pop_por_nome.get(nome, {}).get("populacao"))
    if "codigoIbge" not in df.columns:
        return por_nome
    por_codigo = {str(d["codigo_ibge"]): d["populacao"] for d in pop_por_nome.values()}
    return df["codigoIbge"].map(por_codigo).fillna(por_nome)


def executar_pipeline(
    df_bruto: pd.DataFrame,
    progresso: Optional[Progresso] = None,
) -> dict:
    """
    Roda o pipeline completo sobre um DataFrame de contratos brutos
    (o mesmo formato salvo pelo utils/pncp.py) e devolve um dicionário
    com tudo que o dashboard precisa para renderizar dados reais.
    """

    def avisar(fracao: float, texto: str) -> None:
        if progresso:
            progresso(fracao, texto)

    avisar(0.05, "Tratando os dados...")
    df, log_tratamento = tratar_contratos(df_bruto)

    avisar(0.30, "Classificando por categoria...")
    df = classificar_por_regras(df)
    df, info_classificacao = refinar_outros_com_ml(df)

    avisar(0.55, "Cruzando com a população do IBGE...")
    pop_por_nome = carregar_populacao()
    df["populacao"] = _populacao(df, pop_por_nome)

    avisar(0.70, "Procurando contratos atípicos (Isolation Forest)...")
    df, info_anomalias = detectar_anomalias(df)

    avisar(0.92, "Montando o dashboard...")
    agregados = construir_agregados(df, pop_por_nome)

    avisar(1.0, "Concluído.")

    return {
        "df": df,
        "agregados": agregados,
        "log_tratamento": log_tratamento,
        "info_classificacao": info_classificacao,
        "info_anomalias": info_anomalias,
    }


def construir_agregados(df: pd.DataFrame, pop_por_nome: Optional[dict] = None) -> dict:
    """
    A partir do DataFrame já tratado/classificado (com ou sem anomalias
    detectadas), monta:
      - data_municipios: {nome oficial do GeoJSON: soma do valor}
      - describe_municipios: {nome oficial: describe() do valor}
      - populacao_municipios: {codigo_ibge: {"populacao": n}}
      - kpis: contratos, valor_total, municipios (com contratos), anomalias
      - categorias: top categorias por valor [(nome, largura da barra %, fatia do total %)]
      - top_risco: contratos com risco Alto, ordenados por scoreRisco (com SHAP)
      - fatores_globais: peso médio de cada fator (SHAP) nos contratos Alto
      - alertas_cadastro: contratos com possíveis erros de cadastro
    Funciona também com um df vazio (após aplicar filtros, por exemplo).
    """
    pop_por_nome = pop_por_nome if pop_por_nome is not None else carregar_populacao()
    populacao_municipios = populacao_por_codigo(pop_por_nome)

    if df.empty:
        return {
            "data_municipios": {},
            "describe_municipios": {},
            "populacao_municipios": populacao_municipios,
            "kpis": {
                "contratos": 0,
                "valor_total": 0.0,
                "municipios": 0,
                "anomalias": None,
            },
            "categorias": [],
            "top_risco": pd.DataFrame(),
            "fatores_globais": [],
            "alertas_cadastro": pd.DataFrame(),
        }

    # nome oficial do GeoJSON para cada linha (None quando não casa com nenhum município)
    nome_geojson = _nome_geojson(df)
    df_mapa = df.assign(nomeGeojson=nome_geojson).dropna(subset=["nomeGeojson"])

    data_municipios = df_mapa.groupby("nomeGeojson")["valor"].sum().to_dict()

    describe_municipios = {
        nome: {
            k: (float(v) if pd.notna(v) else 0.0)
            for k, v in grupo["valor"].describe().to_dict().items()
        }
        for nome, grupo in df_mapa.groupby("nomeGeojson")
    }

    # scoreRisco só é > 0 em algum contrato quando o Isolation Forest
    # realmente rodou (por padrão, sem análise aplicada, tudo fica 0.0).
    tem_risco = "scoreRisco" in df.columns and (df["scoreRisco"] > 0).any()
    anomalias_count = int(df["anomalia"].sum()) if tem_risco and "anomalia" in df.columns else None

    kpis = {
        "contratos": int(len(df)),
        "valor_total": float(df["valor"].sum()),
        "municipios": int(df_mapa["nomeGeojson"].nunique()),
        "anomalias": anomalias_count if tem_risco else None,
    }

    categorias_valor = (
        df.groupby("categoriaCurta")["valor"].sum().sort_values(ascending=False)
        if "categoriaCurta" in df.columns
        else pd.Series(dtype=float)
    )
    maior = float(categorias_valor.max()) if not categorias_valor.empty else 1.0
    total = float(categorias_valor.sum()) or 1.0
    categorias = [
        (nome, round(float(valor) / maior * 100, 1), round(float(valor) / total * 100, 1))
        for nome, valor in categorias_valor.head(6).items()
    ]

    if "risco" in df.columns:
        top_risco = (
            df[df["risco"] == "Alto"]
            # percentil no grupo primeiro; o score bruto só desempata
            .sort_values(
                ["scoreRisco", "scoreIF"] if "scoreIF" in df.columns else ["scoreRisco"],
                ascending=False,
            )
            .loc[:, [c for c in [
                "municipio", "grupoModelo", "objeto", "fornecedor", "valor",
                "categoriaCurta", "scoreRisco", "motivoRisco", *COLUNAS_SHAP, *COLUNAS_DESVIO,
            ] if c in df.columns]]
            .head(20)
        )
    else:
        top_risco = pd.DataFrame()

    if "alertaCadastro" in df.columns:
        alertas = df[df["alertaCadastro"] != ""].loc[:, [c for c in [
            "municipio", "objeto", "fornecedor", "valor", "alertaCadastro",
        ] if c in df.columns]]
    else:
        alertas = pd.DataFrame()

    return {
        "data_municipios": data_municipios,
        "describe_municipios": describe_municipios,
        "populacao_municipios": populacao_municipios,
        "kpis": kpis,
        "categorias": categorias,
        "top_risco": top_risco,
        "fatores_globais": fatores_globais(df),
        "alertas_cadastro": alertas,
    }


def aplicar_filtros(
    df: pd.DataFrame,
    ano: Optional[str] = None,
    municipio: Optional[str] = None,
    categoria: Optional[str] = None,
    risco: Optional[str] = None,
    esfera: Optional[str] = None,
) -> pd.DataFrame:
    """Aplica os filtros da sidebar sobre o DataFrame já processado."""
    filtrado = df

    if ano and ano != "Todos":
        filtrado = filtrado[filtrado["ano"].astype(str) == str(ano)]

    if municipio and not municipio.startswith("Todos"):
        alvo = padronizar_texto(municipio)
        filtrado = filtrado[filtrado["municipioNorm"] == alvo]

    if categoria and not categoria.startswith("Todas"):
        filtrado = filtrado[filtrado["categoriaCurta"] == categoria]

    if risco and risco != "Todos" and "risco" in filtrado.columns:
        filtrado = filtrado[filtrado["risco"] == risco]

    if esfera and not esfera.startswith("Todas") and "esfera" in filtrado.columns:
        filtrado = filtrado[filtrado["esfera"] == esfera]

    return filtrado