import streamlit as st

st.set_page_config(
    page_title="Contratos Públicos do Ceará",
    page_icon="📊",
    layout="wide"
)

st.title("Contratos Públicos do Ceará")

st.subheader(
    "Plataforma para visualização e detecção de comportamentos atípicos"
)

st.write(
    """
    Esta plataforma tem como objetivo auxiliar na análise de contratos
    públicos dos municípios do Ceará por meio de indicadores,
    visualizações interativas e técnicas de aprendizado de máquina.
    """
)

st.info("Projeto de Trabalho de Conclusão de Curso.")