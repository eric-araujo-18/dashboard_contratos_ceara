from datetime import date

import pandas as pd
import streamlit as st

from utils import pncp
from utils.mapa import renderizar_mapa
from utils.pipeline import aplicar_filtros, ano_publicacao, construir_agregados, executar_pipeline, fatias_shap


# =========================================================
# CONFIGURAÇÃO
# =========================================================

st.set_page_config(
    page_title="ContratosCE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# HELPERS
# =========================================================

def html(content: str) -> None:
    """Remove indentação e linhas em branco para o Markdown
    não interpretar o conteúdo como bloco de código."""
    linhas = [l.strip() for l in content.splitlines() if l.strip()]
    st.markdown("\n".join(linhas), unsafe_allow_html=True)


def formatar_moeda(valor: float) -> str:
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def formatar_num(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


TODOS_MUNICIPIOS = "Todos os municípios"


def codigo_do_municipio(df, nome):
    """Código IBGE do município escolhido na sidebar (para destacar no mapa)."""
    if df is None or not nome or nome == TODOS_MUNICIPIOS or "codigoIbge" not in df.columns:
        return None
    codigos = df.loc[df["municipio"] == nome, "codigoIbge"].dropna()
    return str(codigos.iloc[0]) if not codigos.empty else None


def municipio_do_codigo(df, codigo):
    """Nome do município (como aparece no filtro) a partir do código clicado no mapa."""
    if df is None or not codigo or "codigoIbge" not in df.columns:
        return None
    nomes = df.loc[df["codigoIbge"] == str(codigo), "municipio"]
    return nomes.iloc[0] if not nomes.empty else None


# =========================================================
# CSS
# =========================================================

html(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&family=JetBrains+Mono:wght@400;600;700&family=Material+Symbols+Outlined&display=swap');

    :root {
        --font-body: "Inter", "Segoe UI", sans-serif;
        --font-title: "Plus Jakarta Sans", "Inter", sans-serif;
        --font-data: "JetBrains Mono", ui-monospace, Consolas, monospace;

        --primary: #006b47;
        --primary-dark: #005235;
        --text: #131b2e;
        --muted: #49607e;
        --surface: #f2f3ff;
        --sidebar-bg: #f0f2ff;
        --segment-bg: #e2e7ff;
        --hover-green: rgba(141, 247, 193, 0.35);
    }

    /* =====================================================
       BASE
    ===================================================== */

    html, body, .stApp,
    .stApp button,
    .stApp input,
    .stApp [data-baseweb="select"] * {
        font-family: var(--font-body) !important;
    }

    .stApp { background: #ffffff; }

    header[data-testid="stHeader"] { background: transparent; }

    /* Esconde só o que não queremos (menu, deploy, decoração, rodapé).
       NÃO esconder o stToolbar inteiro: o botão de reabrir a sidebar
       fica dentro dele em versões novas do Streamlit. */
    div[data-testid="stDecoration"],
    [data-testid="stToolbarActions"],
    [data-testid="stMainMenu"],
    [data-testid="stAppDeployButton"],
    #MainMenu,
    footer { display: none !important; }

    /* Botão de expandir a sidebar sempre visível */
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {
        visibility: visible !important;
        opacity: 1 !important;
        z-index: 1000;
    }

    [data-testid="stExpandSidebarButton"] button,
    [data-testid="stExpandSidebarButton"] svg,
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stSidebarCollapsedControl"] svg,
    [data-testid="collapsedControl"] button,
    [data-testid="collapsedControl"] svg {
        color: var(--primary) !important;
        fill: var(--primary) !important;
    }

    /* Botão de recolher (dentro da sidebar) */
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebarCollapseButton"] svg {
        color: var(--muted) !important;
        fill: var(--muted) !important;
    }

    .block-container {
        max-width: 1500px;
        padding: 2.5rem 2rem 3rem 2rem;
    }

    div[data-testid="stVerticalBlock"] { gap: 1.25rem; }
    .stMarkdown p { margin: 0; margin-bottom: 0.5rem; }

    .icon {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 26px;
        line-height: 1;
        display: inline-block;
        white-space: nowrap;
        font-feature-settings: 'liga';
        -webkit-font-smoothing: antialiased;
        color: var(--primary) !important;
    }

    /* =====================================================
       SIDEBAR
    ===================================================== */

    section[data-testid="stSidebar"][aria-expanded="true"] {
        width: 320px !important;
        min-width: 320px !important;
    }

    section[data-testid="stSidebar"] {
        background: var(--sidebar-bg);
        border-right: none;
    }

    section[data-testid="stSidebar"] > div { padding-top: 0.5rem; }

    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
        gap: 0.4rem;
    }

    .stApp .sidebar-title {
        display: flex;
        align-items: center;
        gap: 10px;
        padding-bottom: 18px;
        border-bottom: 1px solid rgba(189, 202, 192, 0.45);
        color: var(--text) !important;
        font-family: var(--font-title);
        font-size: 19px;
        font-weight: 700;
    }

    .stApp .sidebar-title.secundario {
        margin-top: 28px;
    }

    .stApp .filter-label {
        margin-top: 22px;
        margin-bottom: 22px;
        color: var(--text) !important;
        font-size: 15px;
        font-weight: 600;
    }

    /* =====================================================
       FILTROS: SELECTBOX
    ===================================================== */

    .stApp div[data-baseweb="select"] > div {
        min-height: 44px;
        border: none;
        border-radius: 10px;
        background: #ffffff !important;
        box-shadow: 0 1px 3px rgba(19, 27, 46, 0.10);
        font-size: 13px;
    }

    .stApp div[data-baseweb="select"] span,
    .stApp div[data-baseweb="select"] div,
    .stApp div[data-baseweb="select"] input {
        color: var(--text) !important;
    }

    .stApp div[data-baseweb="select"] svg {
        fill: var(--muted) !important;
        color: var(--muted) !important;
    }

    /* Lista de opções: abre num popup fora da sidebar */
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] li {
        background: #ffffff !important;
        color: var(--text) !important;
        font-size: 13px;
    }

    div[data-baseweb="popover"] li:hover,
    div[data-baseweb="popover"] li[aria-selected="true"] {
        background: var(--hover-green) !important;
        color: var(--primary-dark) !important;
    }

    /* =====================================================
       FILTROS: SEGMENTED CONTROL (ANO)
    ===================================================== */

    div[data-testid="stSegmentedControl"] { width: 100%; }

    div[data-testid="stSegmentedControl"] div[data-baseweb="button-group"] {
        width: 100%;
        gap: 4px;
        padding: 4px;
        border-radius: 10px;
        background: var(--segment-bg);
        flex-wrap: wrap;
    }

    .stApp button[data-testid="stBaseButton-segmented_control"],
    .stApp button[data-testid="stBaseButton-segmented_controlActive"],
    .stApp button[kind="segmented_control"],
    .stApp button[kind="segmented_controlActive"] {
        flex: 1;
        min-height: 34px;
        border: none;
        border-radius: 8px;
    }

    .stApp button[data-testid="stBaseButton-segmented_control"] p,
    .stApp button[data-testid="stBaseButton-segmented_controlActive"] p,
    .stApp button[kind="segmented_control"] p,
    .stApp button[kind="segmented_controlActive"] p {
        font-family: var(--font-data) !important;
        font-size: 11px;
        font-weight: 700;
    }

    /* Inativo */
    .stApp button[data-testid="stBaseButton-segmented_control"],
    .stApp button[kind="segmented_control"] {
        background: transparent !important;
        color: var(--text) !important;
    }

    .stApp button[data-testid="stBaseButton-segmented_control"] p,
    .stApp button[kind="segmented_control"] p {
        color: var(--text) !important;
    }

    .stApp button[data-testid="stBaseButton-segmented_control"]:hover,
    .stApp button[kind="segmented_control"]:hover {
        background: #ffffff !important;
    }

    /* Ativo */
    .stApp button[data-testid="stBaseButton-segmented_controlActive"],
    .stApp button[kind="segmented_controlActive"] {
        background: var(--primary) !important;
        color: #ffffff !important;
    }

    .stApp button[data-testid="stBaseButton-segmented_controlActive"] p,
    .stApp button[kind="segmented_controlActive"] p {
        color: #ffffff !important;
    }

    /* =====================================================
       BASE DE DADOS (download PNCP, upload, botão de análise)
    ===================================================== */

    .stApp div[data-baseweb="datepicker"] input {
        color: var(--text) !important;
    }

    .stApp [data-testid="stFileUploaderDropzone"] {
        background: #ffffff !important;
        border-radius: 10px;
        border: 1px dashed rgba(73, 96, 126, 0.35);
    }

    .stApp [data-testid="stFileUploaderDropzoneInstructions"] span,
    .stApp [data-testid="stFileUploaderDropzoneInstructions"] small {
        color: var(--muted) !important;
    }

    /* Botão secundário (baixar contratos) */
    .stApp section[data-testid="stSidebar"] button[kind="secondary"] {
        background: #ffffff !important;
        color: var(--text) !important;
        border: 1px solid rgba(73, 96, 126, 0.25) !important;
        border-radius: 10px !important;
        font-weight: 600;
    }

    /* Botão primário (fazer análise) */
    .stApp section[data-testid="stSidebar"] button[kind="primary"] {
        background: var(--primary) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700;
    }

    .stApp section[data-testid="stSidebar"] button[kind="primary"]:hover {
        background: var(--primary-dark) !important;
    }

    .stApp section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: var(--muted) !important;
    }

    /* =====================================================
       FONTE DOS DADOS
    ===================================================== */

    .source-card {
        margin-top: 24px;
        padding: 18px;
        border-radius: 16px;
        background: #ffffff;
    }

    .stApp .source-title {
        display: flex;
        align-items: center;
        gap: 10px;
        color: var(--primary) !important;
        font-family: var(--font-title);
        font-size: 15px;
        font-weight: 700;
    }

    .stApp .source-description {
        margin-top: 10px;
        color: var(--muted) !important;
        font-family: var(--font-data);
        font-size: 10px;
        line-height: 1.9;
    }

    /* =====================================================
       CABEÇALHO
    ===================================================== */

    .stApp .page-title {
        margin: 0;
        padding: 0;
        color: var(--text) !important;
        font-family: var(--font-title);
        font-size: 30px;
        font-weight: 700;
        letter-spacing: -0.01em;
    }

    .stApp .page-subtitle {
        margin-top: 6px;
        color: var(--muted) !important;
        font-size: 15px;
    }

    .stApp .page-badge {
        display: inline-block;
        margin-top: 10px;
        padding: 4px 10px;
        border-radius: 999px;
        font-family: var(--font-data);
        font-size: 10px;
        font-weight: 700;
    }

    .stApp .page-badge.exemplo {
        background: rgba(251, 188, 44, 0.20);
        color: #8a5a00 !important;
    }

    .stApp .page-badge.real {
        background: var(--hover-green);
        color: var(--primary-dark) !important;
    }

    /* =====================================================
       KPIs
    ===================================================== */

    .metric-card {
        padding: 22px 18px 20px 18px;
        border-radius: 16px;
        background: var(--surface);
    }

    .stApp .metric-label {
        color: var(--muted) !important;
        font-size: 13px;
    }

    .stApp .metric-value {
        margin-top: 14px;
        color: var(--text) !important;
        font-family: var(--font-title);
        font-size: 28px;
        font-weight: 700;
        line-height: 1;
    }

    /* =====================================================
       CARDS
    ===================================================== */

    .dashboard-card,
    .st-key-card_mapa,
    .st-key-card_risco {
        padding: 22px 22px 26px 22px;
        border-radius: 16px;
        background: var(--surface);
    }

    .st-key-card_mapa,
    .st-key-card_risco { gap: 0.75rem; }

    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
    }

    .stApp .card-title {
        color: var(--text) !important;
        font-family: var(--font-title);
        font-size: 18px;
        font-weight: 700;
    }

    .stApp .card-subtitle {
        margin-top: 6px;
        color: var(--muted) !important;
        font-family: var(--font-data);
        font-size: 10px;
        letter-spacing: 0.02em;
    }

    .stApp .tag {
        padding: 4px 9px;
        border-radius: 6px;
        background: rgba(141, 247, 193, 0.45);
        color: var(--primary-dark) !important;
        font-family: var(--font-data);
        font-size: 10px;
    }

    .stApp .tag.risco {
        background: rgba(251, 188, 44, 0.30);
        color: #8a5a00 !important;
    }

    /* =====================================================
       BARRAS DE CATEGORIA
    ===================================================== */

    .bars {
        margin-top: 30px;
        display: flex;
        flex-direction: column;
        gap: 22px;
    }

    .stApp .bar-label {
        margin-bottom: 8px;
        color: var(--text) !important;
        font-size: 13px;
    }

    .bar-track {
        height: 8px;
        overflow: hidden;
        border-radius: 999px;
        background: #dae2fd;
    }

    .bar-fill {
        height: 100%;
        border-radius: 999px;
        background: var(--primary);
    }

    /* =====================================================
       TABELA DE RISCO
    ===================================================== */

    .st-key-card_risco div[data-testid="stDataFrame"] {
        margin-top: 18px;
    }

    /* =====================================================
       EXPLICAÇÃO DO MODELO (SHAP)
    ===================================================== */

    .st-key-card_shap {
        padding: 22px 22px 26px 22px;
        border-radius: 16px;
        background: var(--surface);
        gap: 0.75rem;
    }

    .bar-fill.shap { background: #d98e04; }

    .stApp .shap-subtitulo {
        margin-top: 8px;
        color: var(--text) !important;
        font-size: 14px;
        font-weight: 600;
    }

    .stApp .shap-nota {
        margin-top: 16px;
        padding: 12px 14px;
        border-radius: 10px;
        background: #ffffff;
        color: var(--muted) !important;
        font-size: 12px;
        line-height: 1.6;
    }

    /* =====================================================
       ERROS DE CADASTRO (expander)
    ===================================================== */

    .stApp [data-testid="stExpander"] details {
        border: none;
        border-radius: 16px;
        background: var(--surface);
    }

    .stApp [data-testid="stExpander"] summary,
    .stApp [data-testid="stExpander"] summary p {
        color: var(--text) !important;
        font-weight: 600;
    }

    /* =====================================================
       TEMA CLARO FORÇADO
       Se o config.toml não for lido (ex.: Streamlit Cloud com o arquivo
       fora da raiz do repositório), o Streamlit segue o tema do navegador
       e os campos da sidebar ficavam escuros. Estas regras garantem o
       visual claro mesmo nesse caso.
    ===================================================== */

    :root { color-scheme: light; }

    section[data-testid="stSidebar"] {
        background: var(--sidebar-bg) !important;
    }

    .stApp div[data-baseweb="input"],
    .stApp div[data-baseweb="input"] > div,
    .stApp div[data-baseweb="base-input"],
    .stApp div[data-baseweb="datepicker"] > div {
        background: #ffffff !important;
        border-radius: 10px;
    }

    .stApp div[data-baseweb="input"] input,
    .stApp div[data-baseweb="base-input"] input {
        background: #ffffff !important;
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
    }

    div[data-baseweb="calendar"],
    div[data-baseweb="calendar"] * {
        background-color: #ffffff;
        color: var(--text);
    }

    .stApp section[data-testid="stSidebar"] label,
    .stApp section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: var(--text) !important;
    }

    .stApp [data-testid="stFileUploaderDropzone"] button {
        background: #ffffff !important;
        color: var(--text) !important;
        border: 1px solid rgba(73, 96, 126, 0.25) !important;
    }

    .stApp [data-testid="stProgress"] div[role="progressbar"] > div > div {
        background: var(--primary) !important;
    }
    </style>
    """
)


# =========================================================
# SIDEBAR — BASE DE DADOS (download PNCP, upload, análise)
# =========================================================

with st.sidebar:

    html(
        """
        <div class="sidebar-title">
        <span class="icon">cloud_download</span>
        Base de Dados
        </div>
        """
    )

    html('<div class="filter-label">Baixar contratos do PNCP</div>')

    hoje = date.today()
    intervalo = st.date_input(
        "Período",
        value=(hoje.replace(day=1), hoje),
        label_visibility="collapsed",
    )
    st.caption("O período considera a data de publicação no PNCP.")

    baixar_clicado = st.button(
        "Baixar contratos",
        width="stretch",
    )

    if baixar_clicado:
        if isinstance(intervalo, tuple) and len(intervalo) == 2:
            data_inicial, data_final = intervalo
            try:
                barra = st.progress(0.0)
                status = st.empty()

                def _progresso_download(fracao: float, texto: str) -> None:
                    barra.progress(min(max(fracao, 0.0), 1.0))
                    status.caption(texto)

                df_baixado, paginas_falhas, info_download = pncp.baixar_contratos(
                    data_inicial, data_final, progresso=_progresso_download
                )
                barra.empty()
                status.empty()

                st.caption(
                    f"PNCP reportou {formatar_num(info_download['total_paginas'])} página(s) no total "
                    f"({formatar_num(info_download['registros_brutos'])} contratos no Brasil todo nesse "
                    f"período, {formatar_num(info_download['registros_uf'])} no Ceará)."
                )

                if paginas_falhas:
                    st.warning(
                        f"⚠️ {len(paginas_falhas)} página(s) do PNCP não responderam mesmo após "
                        f"tentar de novo — os dados baixados estão incompletos. Considere baixar "
                        f"de novo ou reduzir o período."
                    )

                if df_baixado.empty:
                    st.warning("Nenhum contrato encontrado nesse período.")
                else:
                    caminho = pncp.salvar_csv(df_baixado, data_inicial, data_final)
                    st.success(f"{formatar_num(len(df_baixado))} contratos baixados e salvos.")
            except pncp.ErroPNCP as erro:
                st.error(str(erro))
            except Exception as erro:  # falha de rede, parsing, etc.
                st.error(f"Falha ao baixar: {erro}")
        else:
            st.warning("Escolha a data inicial e a data final.")

    html('<div class="filter-label">Base para análise</div>')

    arquivos_disponiveis = pncp.listar_arquivos()
    opcao_upload = "Enviar arquivo (upload)"
    opcoes_base = [p.name for p in arquivos_disponiveis] + [opcao_upload]

    base_escolhida = st.selectbox(
        "Base para análise",
        options=opcoes_base,
        label_visibility="collapsed",
    )

    arquivo_upload = None
    if base_escolhida == opcao_upload:
        arquivo_upload = st.file_uploader(
            "CSV de contratos",
            type="csv",
            label_visibility="collapsed",
        )

    # botão "Fazer análise"
    analisar_clicado = st.button(
        "Fazer análise",
        type="primary",
        width="stretch",
    )

    if analisar_clicado:
        df_bruto = None
        try:
            if base_escolhida == opcao_upload:
                if arquivo_upload is None:
                    st.warning("Envie um arquivo CSV antes de analisar.")
                else:
                    df_bruto = pd.read_csv(arquivo_upload)
            else:
                caminho = next(
                    (p for p in arquivos_disponiveis if p.name == base_escolhida),
                    None,
                )
                if caminho is not None:
                    df_bruto = pd.read_csv(caminho)

            if df_bruto is not None and not df_bruto.empty:
                barra = st.progress(0.0)
                status = st.empty()

                def _progresso(fracao: float, texto: str) -> None:
                    barra.progress(min(max(fracao, 0.0), 1.0))
                    status.caption(texto)

                resultado = executar_pipeline(df_bruto, progresso=_progresso)
                st.session_state["resultado"] = resultado

                barra.empty()
                status.empty()

                n_contratos = resultado["agregados"]["kpis"]["contratos"]
                st.success(f"Análise concluída: {formatar_num(n_contratos)} contratos processados.")
                if resultado.get("aviso_base_final"):
                    st.warning(resultado["aviso_base_final"])

                info_anom = resultado["info_anomalias"]
                if not info_anom.get("aplicado"):
                    st.caption(info_anom.get("motivo", ""))
            elif df_bruto is not None:
                st.warning("O arquivo não tem contratos para analisar.")
        except Exception as erro:
            st.error(f"Não foi possível concluir a análise: {erro}")


# =========================================================
# ESTADO ATUAL DA ANÁLISE
# =========================================================

resultado = st.session_state.get("resultado")
df_real = resultado["df"] if resultado is not None else None
metodo_shap = (resultado or {}).get("info_anomalias", {}).get("metodo_shap") or "valores SHAP"


# =========================================================
# SIDEBAR — FILTROS DINÂMICOS
# =========================================================

with st.sidebar:

    html('<div class="sidebar-title secundario"><span class="icon">tune</span>Filtros Dinâmicos</div>')

    html('<div class="filter-label">Ano de Publicação</div>')
    anos_opcoes = ["Todos"] + (
        sorted(ano_publicacao(df_real).unique(), reverse=True) if df_real is not None else ["2026", "2025"]
    )
    ano = st.segmented_control(
        "Ano",
        options=anos_opcoes,
        default="Todos",
        label_visibility="collapsed",
    )

    html('<div class="filter-label">Município</div>')
    municipios_opcoes = [TODOS_MUNICIPIOS] + (
        sorted(df_real["municipio"].unique()) if df_real is not None
        else ["Crateús", "Fortaleza", "Sobral", "Juazeiro do Norte"]
    )

    # clique no mapa (registrado na execução anterior) vira o filtro de município.
    # Precisa ser feito ANTES de criar o selectbox: o Streamlit não deixa
    # alterar o valor de um widget depois que ele já foi desenhado.
    if "municipio_pendente" in st.session_state:
        st.session_state["filtro_municipio"] = st.session_state.pop("municipio_pendente")
    if st.session_state.get("filtro_municipio") not in municipios_opcoes:
        st.session_state["filtro_municipio"] = TODOS_MUNICIPIOS

    municipio = st.selectbox(
        "Município",
        options=municipios_opcoes,
        key="filtro_municipio",
        label_visibility="collapsed",
    )

    html('<div class="filter-label">Categoria</div>')
    categorias_opcoes = ["Todas as categorias"] + (
        sorted(df_real["categoria"].dropna().unique()) if df_real is not None
        else ["Serviços", "Aquisições", "Obras", "Outros"]
    )
    categoria = st.selectbox(
        "Categoria",
        options=categorias_opcoes,
        label_visibility="collapsed",
    )

    html('<div class="filter-label">Esfera do Órgão</div>')
    esferas_opcoes = ["Todas as esferas"] + (
        sorted(df_real["esfera"].dropna().unique()) if df_real is not None and "esfera" in df_real.columns
        else ["Municipal", "Estadual", "Federal"]
    )
    esfera = st.selectbox(
        "Esfera",
        options=esferas_opcoes,
        label_visibility="collapsed",
        help="O PNCP traz também órgãos estaduais e federais sediados nos municípios "
             "(em Fortaleza, a maioria é do Estado). Escolha Municipal para ver só prefeituras e câmaras.",
    )

    html('<div class="filter-label">Nível de Risco</div>')
    risco = st.selectbox(
        "Nível de Risco",
        options=["Todos", "Alto", "Médio", "Baixo", "Não avaliado"],
        label_visibility="collapsed",
    )

    html(
        """
        <div class="source-card">
        <div class="source-title">
        <span class="icon" style="font-size:24px;">database</span>
        Fonte dos dados
        </div>
        <div class="source-description">
        Portal Nacional de Contratações Públicas (PNCP) e IBGE.
        </div>
        </div>
        """
    )


# =========================================================
# DADOS PARA O DASHBOARD
# =========================================================

if df_real is not None:
    df_filtrado = aplicar_filtros(
        df_real, ano=ano, municipio=municipio, categoria=categoria, risco=risco, esfera=esfera
    )
    agregados = construir_agregados(df_filtrado)

    # o mapa usa todos os filtros MENOS o de município: assim ele continua
    # mostrando o estado inteiro e dá para clicar em outro município
    df_mapa = aplicar_filtros(df_real, ano=ano, categoria=categoria, risco=risco, esfera=esfera)
    agregados_mapa = construir_agregados(df_mapa)

    data_municipios = agregados_mapa["data_municipios"]
    describe_municipios = agregados_mapa["describe_municipios"]
    # população e PIB vêm das colunas da base analisada (inteira, sem filtros)
    populacao_municipios = resultado.get("indicadores_municipios", {})

    kpis_valores = [
        ("Contratos", formatar_num(agregados["kpis"]["contratos"])),
        ("Valor Total", formatar_moeda(agregados["kpis"]["valor_total"])),
        ("Municípios com contratos", formatar_num(agregados["kpis"]["municipios"])),
        (
            "Anomalias",
            formatar_num(agregados["kpis"]["anomalias"])
            if agregados["kpis"]["anomalias"] is not None
            else "—",
        ),
    ]

    categorias = agregados["categorias"]
    contratos_risco = agregados["contratos_risco"]
    fatores = agregados["fatores_globais"]
    alertas = agregados["alertas_cadastro"]
    badge_classe, badge_texto = "real", f"{formatar_num(len(df_filtrado))} contratos analisados"

else:
    # -------- NENHUMA ANÁLISE RODADA AINDA --------
    data_municipios = {}
    describe_municipios = {}
    populacao_municipios = {}

    kpis_valores = [
        ("Contratos", "—"),
        ("Valor Total", "—"),
        ("Municípios com contratos", "—"),
        ("Anomalias", "—"),
    ]

    categorias = []

    contratos_risco = pd.DataFrame()
    fatores = []
    alertas = pd.DataFrame()
    badge_classe, badge_texto = "exemplo", "Nenhuma análise carregada — escolha uma base e clique em Fazer análise"


# =========================================================
# CABEÇALHO
# =========================================================

html(
    f"""
    <div>
    <h1 class="page-title">Visão Geral</h1>
    <div class="page-subtitle">Contratos públicos dos municípios do Ceará</div>
    <span class="page-badge {badge_classe}">{badge_texto}</span>
    </div>
    """
)


# =========================================================
# KPIs
# =========================================================

for col, (label, valor) in zip(st.columns(4, gap="small"), kpis_valores):
    with col:
        html(
            f"""
            <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{valor}</div>
            </div>
            """
        )


# =========================================================
# MAPA (3/5) + CATEGORIAS (2/5)
# =========================================================

map_col, categoria_col = st.columns([3, 2], gap="medium")


# ---------------------------------------------------------
# MAPA
# ---------------------------------------------------------

with map_col:

    with st.container(key="card_mapa"):

        html(
            """
            <div class="card-header">
            <div>
            <div class="card-title">Distribuição Territorial</div>
            <div class="card-subtitle">Valor contratado por município · clique para filtrar</div>
            </div>
            <div class="tag">D3.js</div>
            </div>
            """
        )

        clique = renderizar_mapa(
            data_municipios=data_municipios,
            describe_municipios=describe_municipios,
            populacao_municipios=populacao_municipios,
            selecionado=codigo_do_municipio(df_real, municipio),
        )

    # cada clique traz um carimbo de tempo "t"; só tratamos cliques novos
    if (
        df_real is not None
        and isinstance(clique, dict)
        and clique.get("t") != st.session_state.get("mapa_ultimo_clique")
    ):
        st.session_state["mapa_ultimo_clique"] = clique.get("t")

        if clique.get("codigo") is None:
            novo_municipio = TODOS_MUNICIPIOS
        else:
            novo_municipio = municipio_do_codigo(df_real, clique["codigo"])
            if novo_municipio is None:
                st.toast(f"{clique.get('nome')} não tem contratos nesta base.")

        if novo_municipio is not None and novo_municipio != municipio:
            st.session_state["municipio_pendente"] = novo_municipio
            st.rerun()


# ---------------------------------------------------------
# CATEGORIAS
# ---------------------------------------------------------

with categoria_col:

    if categorias:
        barras = "".join(
            f'<div>'
            f'<div class="bar-label">{nome} · {str(fatia).replace(".", ",")}%</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{largura}%;"></div></div>'
            f'</div>'
            for nome, largura, fatia in categorias
        )
    elif df_real is None:
        barras = '<div class="bar-label">Rode uma análise para ver as categorias.</div>'
    else:
        barras = '<div class="bar-label">Nenhum contrato encontrado com esses filtros.</div>'

    html(
        f"""
        <div class="dashboard-card">
        <div class="card-title">Categorias</div>
        <div class="card-subtitle">Distribuição do valor contratado</div>
        <div class="bars">{barras}</div>
        </div>
        """
    )


# =========================================================
# CONTRATOS POR NÍVEL DE RISCO (com paginação)
# =========================================================

NIVEIS_RISCO = ["Alto", "Médio", "Baixo", "Não avaliado"]
DESCRICAO_NIVEL = {
    "Alto": "5% mais atípicos de cada grupo de comparação, do mais atípico ao menos atípico",
    "Médio": "Faixa seguinte de 10% (índice de 85 a 95), do mais atípico ao menos atípico",
    "Baixo": "Demais contratos avaliados pelo modelo, do mais atípico ao menos atípico",
    "Não avaliado": "Fora do modelo: alienações, órgãos sem esfera definida e grupos pequenos",
}
OPCOES_POR_PAGINA = [10, 20, 50, 100]

nivel = None
pagina_risco = pd.DataFrame()  # contratos da página atual (a explicação SHAP usa os mesmos)

if not contratos_risco.empty:

    contagem = contratos_risco["risco"].value_counts()
    niveis = [n for n in NIVEIS_RISCO if contagem.get(n, 0) > 0]
    # nova análise ou outro filtro lateral de risco: volta para o nível mais alto disponível;
    # fora isso, o nível escolhido continua valendo enquanto existir com os filtros atuais
    if st.session_state.get("risco_contexto") != (id(df_real), risco):
        st.session_state["risco_contexto"] = (id(df_real), risco)
        st.session_state["risco_nivel"] = niveis[0]
    if st.session_state.get("risco_nivel") not in niveis:
        st.session_state["risco_nivel"] = niveis[0]
    nivel = st.session_state["risco_nivel"]

    linhas = contratos_risco[contratos_risco["risco"] == nivel]
    st.session_state.setdefault("risco_por_pagina", 20)
    por_pagina = st.session_state["risco_por_pagina"]
    n_paginas = max(1, -(-len(linhas) // por_pagina))

    # outra lista (nova análise, outro nível, filtro ou tamanho de página): volta para a página 1
    lista = (id(df_real), nivel, por_pagina, ano, municipio, categoria, esfera, risco)
    if st.session_state.get("risco_lista") != lista:
        st.session_state["risco_lista"] = lista
        st.session_state["risco_pagina"] = 1
    pagina = min(max(int(st.session_state.get("risco_pagina", 1)), 1), n_paginas)
    st.session_state["risco_pagina"] = pagina

    inicio = (pagina - 1) * por_pagina
    pagina_risco = linhas.iloc[inicio:inicio + por_pagina]

    with st.container(key="card_risco"):

        html(
            f"""
            <div class="card-header">
            <div>
            <div class="card-title">Contratos por Nível de Risco</div>
            <div class="card-subtitle">{DESCRICAO_NIVEL[nivel]}</div>
            </div>
            <div class="tag risco">Isolation Forest</div>
            </div>
            """
        )

        st.segmented_control(
            "Nível de risco",
            options=niveis,
            required=True,
            format_func=lambda n: f"{n} ({formatar_num(int(contagem[n]))})",
            key="risco_nivel",
            label_visibility="collapsed",
        )

        tabela = pagina_risco.drop(
            columns=[c for c in pagina_risco.columns if c == "risco" or c.startswith(("shap_", "desvio_"))]
        )
        # posição do contrato na lista do nível (continua de uma página para a outra)
        tabela.insert(0, "posicao", range(inicio + 1, inicio + len(tabela) + 1))
        if nivel == "Baixo":
            # o SHAP só é calculado para Alto e Médio: a coluna de fatores ficaria vazia
            tabela = tabela.drop(columns=["motivoRisco"], errors="ignore")
        if nivel == "Não avaliado":
            # sem índice (o modelo não rodou); o motivo diz por que ficou de fora
            tabela = tabela.drop(columns=["scoreRisco"], errors="ignore")

        coluna_motivo = "Motivo" if nivel == "Não avaliado" else "Principais fatores (SHAP)"
        tabela = tabela.rename(
            columns={
                "posicao": "Nº",
                "municipio": "Município",
                "grupoModelo": "Comparado com",
                "objeto": "Objeto do contrato",
                "fornecedor": "Fornecedor",
                "valor": "Valor (R$)",
                "categoria": "Categoria",
                "scoreRisco": "Índice de risco",
                "motivoRisco": coluna_motivo,
            }
        )

        st.dataframe(
            tabela,
            width="stretch",
            hide_index=True,
            column_config={
                "Nº": st.column_config.NumberColumn(format="%d", width="small"),
                "Valor (R$)": st.column_config.NumberColumn(format="R$ %.f"),
                "Índice de risco": st.column_config.NumberColumn(
                    format="%.1f",
                    help="Percentil de atipicidade dentro do grupo de comparação (esfera do órgão e tipo de documento).",
                ),
                "Comparado com": st.column_config.TextColumn(
                    help="Cada grupo tem o seu próprio modelo: o contrato só é comparado com contratos parecidos.",
                ),
                "Principais fatores (SHAP)": st.column_config.TextColumn(
                    help="Atributos que mais pesaram, com a fatia da contribuição SHAP entre colchetes.",
                    width="large",
                ),
                "Motivo": st.column_config.TextColumn(
                    help="Por que o contrato ficou fora do modelo.",
                    width="large",
                ),
            },
        )

        col_info, col_pagina, col_tamanho = st.columns([4, 1, 1], vertical_alignment="bottom")
        with col_info:
            st.caption(
                f"Mostrando {formatar_num(inicio + 1)}–{formatar_num(inicio + len(pagina_risco))} "
                f"de {formatar_num(len(linhas))} contratos · página {pagina} de {n_paginas}"
            )
        with col_pagina:
            st.number_input("Página", min_value=1, max_value=n_paginas, step=1, key="risco_pagina")
        with col_tamanho:
            st.selectbox("Por página", OPCOES_POR_PAGINA, key="risco_por_pagina")


# =========================================================
# EXPLICAÇÃO DO MODELO (SHAP)
# =========================================================

def barras_html(itens, classe="") -> str:
    if not itens:
        return '<div class="bar-label">Sem contribuições positivas para exibir.</div>'
    return "".join(
        f'<div>'
        f'<div class="bar-label">{nome} · {str(round(pct, 1)).replace(".", ",")}%</div>'
        f'<div class="bar-track"><div class="bar-fill {classe}" style="width:{pct:.1f}%;"></div></div>'
        f'</div>'
        for nome, pct in itens
    )


# o SHAP só existe para Alto e Médio; a explicação usa os contratos da página atual
explicaveis = pagina_risco if nivel in ("Alto", "Médio") else pd.DataFrame()

if not contratos_risco.empty and contratos_risco["risco"].isin(["Alto", "Médio"]).any():

    with st.container(key="card_shap"):

        html(
            f"""
            <div class="card-header">
            <div>
            <div class="card-title">Explicação do Modelo</div>
            <div class="card-subtitle">Quanto cada atributo contribuiu para o contrato ser considerado atípico · {metodo_shap}</div>
            </div>
            <div class="tag risco">SHAP</div>
            </div>
            """
        )

        col_contrato, col_geral = st.columns([3, 2], gap="large")

        with col_contrato:
            html('<div class="shap-subtitulo">Por que este contrato foi apontado?</div>')

            if explicaveis.empty:
                html(
                    """
                    <div class="shap-nota">
                    Os valores SHAP são calculados só para os contratos de risco Alto e Médio.
                    Escolha um desses níveis na tabela acima para ver a explicação de um contrato.
                    </div>
                    """
                )
            else:
                opcoes = list(explicaveis.index)
                # mesmo número da coluna "Nº" da tabela
                posicao = {i: inicio + k + 1 for k, i in enumerate(opcoes)}
                # outra página ou outro nível: começa pelo primeiro contrato da página
                if st.session_state.get("shap_contrato") not in opcoes:
                    st.session_state["shap_contrato"] = opcoes[0]
                escolhido = st.selectbox(
                    "Contrato",
                    options=opcoes,
                    format_func=lambda i: (
                        f"Nº {posicao[i]} · {explicaveis.at[i, 'municipio']} · "
                        f"{explicaveis.at[i, 'categoria']} · {formatar_moeda(explicaveis.at[i, 'valor'])}"
                    ),
                    label_visibility="collapsed",
                    key="shap_contrato",
                )
                linha = explicaveis.loc[escolhido]
                faixa = (
                    "está entre os 5% mais atípicos desse grupo"
                    if linha.get("risco") == "Alto"
                    else "está na faixa seguinte de 10% (índice de 85 a 95) desse grupo"
                )

                html(f'<div class="bars">{barras_html(fatias_shap(linha), "shap")}</div>')
                html(
                    f"""
                    <div class="shap-nota">
                    <b>{linha.get("motivoRisco", "")}</b><br>
                    Índice {str(linha.get("scoreRisco", "")).replace(".", ",")} dentro do grupo
                    “{linha.get("grupoModelo", "")}”: {faixa}.
                    </div>
                    """
                )

        with col_geral:
            html('<div class="shap-subtitulo">O que mais pesa nos contratos de risco alto</div>')
            html(f'<div class="bars">{barras_html(fatores)}</div>')
            html(
                """
                <div class="shap-nota">
                Média das contribuições SHAP dos contratos de risco Alto com os filtros atuais.
                Atipicidade estatística não significa irregularidade: indica onde vale olhar primeiro.
                </div>
                """
            )


# =========================================================
# POSSÍVEIS ERROS DE CADASTRO
# =========================================================

if df_real is not None and not alertas.empty:

    with st.expander(f"Possíveis erros de cadastro ({formatar_num(len(alertas))})"):
        st.caption(
            "Contratos com valor simbólico, datas inconsistentes ou assinatura depois da "
            "publicação. Ficam separados do risco porque costumam ser erro de preenchimento."
        )
        st.dataframe(
            alertas.rename(
                columns={
                    "municipio": "Município",
                    "objeto": "Objeto do contrato",
                    "fornecedor": "Fornecedor",
                    "valor": "Valor (R$)",
                    "alertaCadastro": "Alerta",
                }
            ),
            width="stretch",
            hide_index=True,
            column_config={"Valor (R$)": st.column_config.NumberColumn(format="R$ %.f")},
        )