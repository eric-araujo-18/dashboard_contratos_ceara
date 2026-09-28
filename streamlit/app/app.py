import streamlit as st

from utils.mapa import renderizar_mapa


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
# HELPER HTML
# Remove indentação e linhas em branco para o Markdown
# não interpretar o conteúdo como bloco de código.
# =========================================================

def html(content: str) -> None:
    linhas = [l.strip() for l in content.splitlines() if l.strip()]
    st.markdown("\n".join(linhas), unsafe_allow_html=True)


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
    .stMarkdown p { margin: 0; }

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
        width: 300px !important;
        min-width: 300px !important;
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

    .stApp .filter-label {
        margin-top: 22px;
        margin-bottom: 12px;
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
       FONTE DOS DADOS
    ===================================================== */

    .source-card {
        margin-top: 60px;
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
    .st-key-card_mapa {
        padding: 22px 22px 26px 22px;
        border-radius: 16px;
        background: var(--surface);
    }

    .st-key-card_mapa { gap: 0.75rem; }

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
    </style>
    """
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    html(
        """
        <div class="sidebar-title">
        <span class="icon">tune</span>
        Filtros Dinâmicos
        </div>
        """
    )

    html('<div class="filter-label">Ano do Contrato</div>')
    ano = st.segmented_control(
        "Ano",
        options=["2026", "2025", "Todos"],
        default="2026",
        label_visibility="collapsed",
    )

    html('<div class="filter-label">Município</div>')
    municipio = st.selectbox(
        "Município",
        options=[
            "Todos os municípios",
            "Crateús",
            "Fortaleza",
            "Sobral",
            "Juazeiro do Norte",
        ],
        label_visibility="collapsed",
    )

    html('<div class="filter-label">Categoria</div>')
    categoria = st.selectbox(
        "Categoria",
        options=["Todas as categorias", "Serviços", "Aquisições", "Obras", "Outros"],
        label_visibility="collapsed",
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
# CABEÇALHO
# =========================================================

html(
    """
    <div>
    <h1 class="page-title">Visão Geral</h1>
    <div class="page-subtitle">Contratos públicos dos municípios do Ceará</div>
    </div>
    """
)


# =========================================================
# KPIs
# =========================================================

kpis = [
    ("Contratos", "—"),
    ("Valor Total", "—"),
    ("Municípios", "184"),
    ("Anomalias", "—"),
]

for col, (label, valor) in zip(st.columns(4, gap="small"), kpis):
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
            <div class="card-subtitle">Valor contratado por município</div>
            </div>
            <div class="tag">D3.js</div>
            </div>
            """
        )

        # -------- DADOS TEMPORÁRIOS --------
        dados_teste = {
            "Fortaleza": 5_000_000,
            "Crateús": 1_200_000,
            "Sobral": 2_800_000,
            "Juazeiro do Norte": 3_500_000,
        }

        describe_teste = {
            "Fortaleza": {
                "count": 20, "mean": 250_000, "std": 85_000, "min": 30_000,
                "25%": 120_000, "50%": 210_000, "75%": 340_000, "max": 800_000,
            },
            "Crateús": {
                "count": 8, "mean": 150_000, "std": 40_000, "min": 50_000,
                "25%": 90_000, "50%": 140_000, "75%": 200_000, "max": 320_000,
            },
            "Sobral": {
                "count": 14, "mean": 200_000, "std": 55_000, "min": 35_000,
                "25%": 110_000, "50%": 180_000, "75%": 290_000, "max": 620_000,
            },
            "Juazeiro do Norte": {
                "count": 18, "mean": 194_444, "std": 67_000, "min": 25_000,
                "25%": 95_000, "50%": 170_000, "75%": 280_000, "max": 710_000,
            },
        }

        populacao_teste = {
            "2304400": {"populacao": 2_600_000},
            "2304103": {"populacao": 75_000},
            "2312908": {"populacao": 210_000},
            "2307304": {"populacao": 280_000},
        }

        renderizar_mapa(
            data_municipios=dados_teste,
            describe_municipios=describe_teste,
            populacao_municipios=populacao_teste,
        )


# ---------------------------------------------------------
# CATEGORIAS
# ---------------------------------------------------------

with categoria_col:

    categorias = [
        ("Serviços", 82),
        ("Aquisições", 68),
        ("Obras", 49),
        ("Outros", 31),
    ]

    barras = "".join(
        f'<div>'
        f'<div class="bar-label">{nome}</div>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%;"></div></div>'
        f'</div>'
        for nome, pct in categorias
    )

    html(
        f"""
        <div class="dashboard-card">
        <div class="card-title">Categorias</div>
        <div class="card-subtitle">Distribuição do valor contratado</div>
        <div class="bars">{barras}</div>
        </div>
        """
    )