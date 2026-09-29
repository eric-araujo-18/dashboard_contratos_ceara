"""
Orquestra o pipeline completo: tratamento -> classificação (regras + ML)
-> população (IBGE) -> detecção de anomalias (Isolation Forest) ->
agregados prontos para o dashboard (KPIs, mapa, categorias, ranking de risco).

É este módulo que o botão "Fazer análise" do app.py chama.
"""
from __future__ import annotations

from typing import Callable, Optional

import pandas as pd

from utils.anomalias import detectar_anomalias
from utils.classificador import classificar_por_regras, refinar_outros_com_ml
from utils.ibge import carregar_populacao, populacao_por_codigo
from utils.mapa import carregar_geojson
from utils.tratamento import padronizar_texto, tratar_contratos

Progresso = Callable[[float, str], None]


def _mapa_nome_geojson() -> dict:
    """{nome município normalizado: nome oficial exatamente como está no GeoJSON}."""
    geojson = carregar_geojson()
    return {
        padronizar_texto(feature["properties"]["name"]): feature["properties"]["name"]
        for feature in geojson["features"]
    }


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
    df["populacao"] = df["municipioNorm"].map(
        lambda nome: pop_por_nome.get(nome, {}).get("populacao")
    )

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
      - kpis: contratos, valor_total, municipios, anomalias
      - categorias: top categorias por valor contratado
      - top_risco: contratos com risco Alto, ordenados por scoreRisco
    Funciona também com um df vazio (após aplicar filtros, por exemplo).
    """
    pop_por_nome = pop_por_nome if pop_por_nome is not None else carregar_populacao()
    populacao_municipios = populacao_por_codigo(pop_por_nome)

    geojson_por_norm = _mapa_nome_geojson()
    total_municipios_ceara = len(geojson_por_norm)

    if df.empty:
        return {
            "data_municipios": {},
            "describe_municipios": {},
            "populacao_municipios": populacao_municipios,
            "kpis": {
                "contratos": 0,
                "valor_total": 0.0,
                "municipios": total_municipios_ceara,
                "anomalias": None,
            },
            "categorias": [],
            "top_risco": pd.DataFrame(),
        }

    # nome oficial do GeoJSON para cada linha (None quando não casa com nenhum município)
    nome_geojson = df["municipioNorm"].map(geojson_por_norm)
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
        "municipios": total_municipios_ceara,
        "anomalias": anomalias_count if tem_risco else None,
    }

    categorias_valor = (
        df.groupby("categoriaCurta")["valor"].sum().sort_values(ascending=False)
        if "categoriaCurta" in df.columns
        else pd.Series(dtype=float)
    )
    maior = float(categorias_valor.max()) if not categorias_valor.empty else 1.0
    categorias = [
        (nome, round(float(valor) / maior * 100, 1))
        for nome, valor in categorias_valor.head(6).items()
    ]

    if "risco" in df.columns:
        top_risco = (
            df[df["risco"] == "Alto"]
            .sort_values("scoreRisco", ascending=False)
            .loc[:, [c for c in [
                "municipio", "objeto", "fornecedor", "valor",
                "categoriaCurta", "scoreRisco", "motivoRisco",
            ] if c in df.columns]]
            .head(20)
        )
    else:
        top_risco = pd.DataFrame()

    return {
        "data_municipios": data_municipios,
        "describe_municipios": describe_municipios,
        "populacao_municipios": populacao_municipios,
        "kpis": kpis,
        "categorias": categorias,
        "top_risco": top_risco,
    }


def aplicar_filtros(
    df: pd.DataFrame,
    ano: Optional[str] = None,
    municipio: Optional[str] = None,
    categoria: Optional[str] = None,
    risco: Optional[str] = None,
) -> pd.DataFrame:
    """Aplica os filtros da sidebar sobre o DataFrame já processado."""
    filtrado = df

    if ano and ano != "Todos":
        filtrado = filtrado[filtrado["ano"] == ano]

    if municipio and not municipio.startswith("Todos"):
        alvo = padronizar_texto(municipio)
        filtrado = filtrado[filtrado["municipioNorm"] == alvo]

    if categoria and not categoria.startswith("Todas"):
        filtrado = filtrado[filtrado["categoriaCurta"] == categoria]

    if risco and risco != "Todos" and "risco" in filtrado.columns:
        filtrado = filtrado[filtrado["risco"] == risco]

    return filtrado