"""
Mapa do Ceará (D3.js) como componente do Streamlit.

É um componente "de verdade" (e não só um iframe estático) para que o
clique num município volte para o Python e vire o filtro do dashboard.
O HTML fica em app/components/mapa_ceara/index.html e recebe os dados
pelo protocolo de componentes do Streamlit.
"""
import json

import streamlit as st
import streamlit.components.v1 as components

from utils.config import BASE_DIR, GEOJSON_PATH

PASTA_COMPONENTE = BASE_DIR / "app" / "components" / "mapa_ceara"
CAMINHO_GEOJSON = GEOJSON_PATH

_componente_mapa = components.declare_component("mapa_ceara", path=str(PASTA_COMPONENTE))


@st.cache_data
def carregar_geojson():
    with open(CAMINHO_GEOJSON, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def renderizar_mapa(
    data_municipios=None,
    describe_municipios=None,
    populacao_municipios=None,
    selecionado=None,
    key="mapa_ceara",
):
    """
    Desenha o mapa e devolve o último clique:
      {"codigo": "2304103", "nome": "Crateús", "t": 1727...}  -> clicou num município
      {"codigo": None, "nome": None, "t": ...}                -> clicou fora (limpar)
      None                                                    -> ainda não houve clique
    `selecionado` é o código IBGE do município a destacar (sincroniza com a sidebar).
    """
    return _componente_mapa(
        data=data_municipios or {},
        describe=describe_municipios or {},
        populacao=populacao_municipios or {},
        geojson=carregar_geojson(),
        selecionado=selecionado,
        key=key,
        default=None,
    )