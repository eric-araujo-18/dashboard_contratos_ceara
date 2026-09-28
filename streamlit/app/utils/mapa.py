import json
from pathlib import Path

import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[2]

CAMINHO_HTML = BASE_DIR / "app" / "components" / "mapa_ceara.html"
CAMINHO_GEOJSON = BASE_DIR / "data" / "geo" / "ceara.geojson.json"


@st.cache_data
def carregar_geojson():
    with open(CAMINHO_GEOJSON, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


@st.cache_data
def carregar_html():
    with open(CAMINHO_HTML, "r", encoding="utf-8") as arquivo:
        return arquivo.read()


def renderizar_mapa(
    data_municipios=None,
    describe_municipios=None,
    populacao_municipios=None,
):
    data_municipios = data_municipios or {}
    describe_municipios = describe_municipios or {}
    populacao_municipios = populacao_municipios or {}

    substituicoes = {
        "__DATA_FROM_STREAMLIT__": data_municipios,
        "__DESCRIBE_FROM_STREAMLIT__": describe_municipios,
        "__POPULACAO_FROM_IBGE__": populacao_municipios,
        "__GEOJSON__": carregar_geojson(),
    }

    conteudo = carregar_html()

    for marcador, valor in substituicoes.items():
        conteudo = conteudo.replace(
            marcador,
            json.dumps(valor, ensure_ascii=False),
        )

    # Requer Streamlit >= 1.56
    st.iframe(conteudo, height=840)
