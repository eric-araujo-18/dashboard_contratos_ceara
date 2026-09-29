from datetime import date

import pandas as pd
import streamlit as st

from utils import pncp
from utils.mapa import renderizar_mapa
from utils.pipeline import aplicar_filtros, construir_agregados, executar_pipeline


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
        use_container_width=True,
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

    analisar_clicado = st.button(
        "Fazer análise",
        type="primary",
        use_container_width=True,
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


# =========================================================
# SIDEBAR — FILTROS DINÂMICOS
# =========================================================

with st.sidebar:

    html('<div class="sidebar-title secundario"><span class="icon">tune</span>Filtros Dinâmicos</div>')

    html('<div class="filter-label">Ano de Publicação</div>')
    anos_opcoes = ["Todos"] + (
        sorted(df_real["ano"].astype(str).unique(), reverse=True) if df_real is not None else ["2026", "2025"]
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
        sorted(df_real["categoriaCurta"].dropna().unique()) if df_real is not None
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
        options=["Todos", "Baixo", "Médio", "Alto"],
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
    populacao_municipios = agregados_mapa["populacao_municipios"]

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
    top_risco = agregados["top_risco"]
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

    top_risco = pd.DataFrame()
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
# TOP CONTRATOS COM MAIOR RISCO
# =========================================================

if not top_risco.empty:

    with st.container(key="card_risco"):

        html(
            """
            <div class="card-header">
            <div>
            <div class="card-title">Contratos com Maior Risco</div>
            <div class="card-subtitle">Apontados pelo Isolation Forest, do mais atípico ao menos atípico</div>
            </div>
            <div class="tag risco">Isolation Forest</div>
            </div>
            """
        )

        tabela = top_risco.rename(
            columns={
                "municipio": "Município",
                "esfera": "Esfera",
                "objeto": "Objeto do contrato",
                "fornecedor": "Fornecedor",
                "valor": "Valor (R$)",
                "categoriaCurta": "Categoria",
                "scoreRisco": "Índice de risco",
                "motivoRisco": "Motivo",
            }
        )

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Valor (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Índice de risco": st.column_config.NumberColumn(format="%.1f"),
            },
        )