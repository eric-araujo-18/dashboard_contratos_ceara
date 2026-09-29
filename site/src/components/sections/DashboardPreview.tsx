/* =========================================================
   PRÉVIA DO DASHBOARD
   Reproduz a tela do Streamlit (sidebar, KPIs, mapa, categorias
   e ranking de risco) com os números da base de contratos
   publicados no PNCP entre jan. e abr. de 2026.
   Para atualizar, troque os valores das constantes abaixo e
   gere de novo o arquivo public/mapa-ceara-preview.svg.
========================================================= */

const STREAMLIT_URL =
  process.env.NEXT_PUBLIC_STREAMLIT_URL || "#";

const PERIODO_BASE = "2026/01/01 – 2026/04/11";
const ARQUIVO_BASE = "contratos_ceara.csv";

const KPIS = [
  { label: "Contratos", value: "22.324" },
  { label: "Valor Total", value: "R$ 15.867.226.759,73" },
  { label: "Municípios com contratos", value: "182" },
  { label: "Anomalias", value: "1.117" },
];

const CATEGORIAS = [
  { nome: "Obras e engenharia", largura: 100, fatia: "36,0" },
  { nome: "Material de limpeza", largura: 40.7, fatia: "14,7" },
  { nome: "Transporte escolar", largura: 34, fatia: "12,2" },
  { nome: "Equipamentos", largura: 21.9, fatia: "7,9" },
  { nome: "Alimentos", largura: 10.9, fatia: "3,9" },
  { nome: "Serviços administrativos", largura: 9.1, fatia: "3,3" },
];

const LEGENDA_MAPA = {
  min: "R$ 1.860,00",
  max: "R$ 6.191.630.830,01",
};

const TOP_RISCO = [
  {
    municipio: "Tianguá",
    esfera: "Municipal",
    categoria: "Tecnologia da informação",
    valor: "R$ 38.444.005,08",
    indice: "100.0",
    motivo:
      "Valor 2298.0x a mediana da categoria; Fornecedor concentra 71% do valor do município; Vigência superior a 5 anos",
  },
  {
    municipio: "Amontada",
    esfera: "Municipal",
    categoria: "Alimentos",
    valor: "R$ 1,00",
    indice: "100.0",
    motivo: "Combinação atípica (destaque: Vigência muito curta)",
  },
  {
    municipio: "Aurora",
    esfera: "Municipal",
    categoria: "Alimentos",
    valor: "R$ 204.560.000,00",
    indice: "100.0",
    motivo:
      "Valor 9167.2x a mediana da categoria; Valor por habitante muito alto para o município; Fornecedor concentra 99% do valor do município",
  },
  {
    municipio: "Beberibe",
    esfera: "Municipal",
    categoria: "Locação",
    valor: "R$ 19.375.878,36",
    indice: "100.0",
    motivo: "Valor 403.7x a mediana da categoria",
  },
  {
    municipio: "Quixelô",
    esfera: "Municipal",
    categoria: "Equipamentos",
    valor: "R$ 900.527.090,00",
    indice: "100.0",
    motivo:
      "Valor 47254.2x a mediana da categoria; Valor por habitante muito alto para o município; Fornecedor concentra 99% do valor do município",
  },
];

function hostDoDashboard(url: string) {
  try {
    return new URL(url).host;
  } catch {
    return "contratos-ce.streamlit.app";
  }
}


/* =========================================================
   SEÇÃO
========================================================= */

export default function DashboardPreview() {
  return (
    <section
      id="analises"
      className="bg-[#f2f3ff] py-20"
    >
      <div
        className="
          mx-auto max-w-7xl
          px-6 lg:px-12
        "
      >
        <div
          className="
            mb-10
            flex flex-col gap-4
            md:flex-row
            md:items-end
            md:justify-between
          "
        >
          <div>
            <span
              className="
                font-data
                text-[11px]
                font-bold
                uppercase
                tracking-wider
                text-[#006b47]
              "
            >
              Plataforma Interativa
            </span>

            <h2
              className="
                font-title
                mt-2 text-3xl
                font-bold
                md:text-4xl
              "
            >
              Uma visão do Dashboard
            </h2>

            <p
              className="
                mt-3 max-w-2xl
                leading-7
                text-[#3e4942]
              "
            >
              Indicadores, filtros,
              visualizações geográficas,
              estatísticas e ranking de
              contratos com maiores pontuações
              de anomalia.
            </p>
          </div>

          <a
            href={STREAMLIT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="
              inline-flex
              items-center gap-2
              self-start
              rounded-xl
              bg-[#006b47]
              px-5 py-3
              font-semibold
              text-white
              shadow-sm
              transition
              hover:bg-[#005235]
            "
          >
            Abrir em tela cheia

            <span className="material-symbols-outlined text-[17px]">
              open_in_new
            </span>
          </a>
        </div>

        <div
          className="
            dashboard-shadow
            overflow-hidden
            rounded-2xl
            bg-white
          "
        >
          <BrowserBar />

          <div
            className="
              grid
              grid-cols-1
              lg:grid-cols-12
            "
          >
            <DashboardSidebar />

            <DashboardContent />
          </div>
        </div>

        <p
          className="
            font-data
            mt-4 text-center
            text-[10px]
            text-[#49607e]
          "
        >
          Prévia estática com a base de contratos
          publicados no PNCP entre janeiro e abril de 2026.
        </p>
      </div>
    </section>
  );
}


/* =========================================================
   BARRA DO NAVEGADOR
========================================================= */

function BrowserBar() {
  return (
    <div
      className="
        flex items-center
        justify-between
        gap-4
        bg-[#e2e7ff]
        px-4 py-3
      "
    >
      <div className="flex items-center gap-3">
        <div className="flex gap-1.5">
          <span className="h-3 w-3 rounded-full bg-[#ba1a1a]/70" />
          <span className="h-3 w-3 rounded-full bg-[#fbbc2c]" />
          <span className="h-3 w-3 rounded-full bg-[#71dba6]" />
        </div>

        <div
          className="
            font-data
            hidden items-center gap-2
            rounded-md
            bg-white
            px-3 py-1
            text-[10px]
            text-[#49607e]
            sm:flex
          "
        >
          <span
            className="
              material-symbols-outlined
              text-[14px]
              text-[#006b47]
            "
          >
            lock
          </span>

          {hostDoDashboard(STREAMLIT_URL)}
        </div>
      </div>

      <div
        className="
          font-data
          flex items-center gap-1.5
          rounded-md
          bg-[#8df7c1]/50
          px-2 py-1
          text-[9px]
          font-semibold
          text-[#002113]
        "
      >
        <span
          className="
            pulse-dot
            h-2 w-2
            rounded-full
            bg-[#006b47]
          "
        />

        LIVE EXECUTION
      </div>
    </div>
  );
}


/* =========================================================
   SIDEBAR (Base de Dados + Filtros Dinâmicos)
========================================================= */

function DashboardSidebar() {
  return (
    <aside
      className="
        flex flex-col gap-4
        bg-[#f0f2ff]
        p-5
        lg:col-span-3
      "
    >
      {/* ---------- BASE DE DADOS ---------- */}

      <SidebarTitle icon="cloud_download" text="Base de Dados" />

      <div>
        <FilterLabel text="Baixar contratos do PNCP" />

        <FakeField text={PERIODO_BASE} icon="calendar_month" />

        <p className="mt-1.5 text-[10px] text-[#49607e]">
          O período considera a data de publicação no PNCP.
        </p>

        <div
          className="
            mt-2
            rounded-lg
            border border-[#49607e]/25
            bg-white
            py-2
            text-center
            text-xs
            font-semibold
          "
        >
          Baixar contratos
        </div>
      </div>

      <div>
        <FilterLabel text="Base para análise" />

        <FakeField text={ARQUIVO_BASE} icon="expand_more" />

        <div
          className="
            mt-2
            rounded-lg
            bg-[#006b47]
            py-2
            text-center
            text-xs
            font-bold
            text-white
          "
        >
          Fazer análise
        </div>
      </div>

      {/* ---------- FILTROS DINÂMICOS ---------- */}

      <div className="mt-3">
        <SidebarTitle icon="tune" text="Filtros Dinâmicos" />
      </div>

      <div>
        <FilterLabel text="Ano de Publicação" />

        <div
          className="
            grid grid-cols-2
            gap-1
            rounded-lg
            bg-[#e2e7ff]
            p-1
          "
        >
          <span
            className="
              font-data
              rounded-md
              bg-[#006b47]
              py-1.5
              text-center
              text-[10px]
              font-bold
              text-white
            "
          >
            Todos
          </span>

          <span
            className="
              font-data
              rounded-md
              py-1.5
              text-center
              text-[10px]
              font-bold
            "
          >
            2026
          </span>
        </div>
      </div>

      <FakeSelect title="Município" text="Todos os municípios" />
      <FakeSelect title="Categoria" text="Todas as categorias" />
      <FakeSelect title="Esfera do Órgão" text="Todas as esferas" />
      <FakeSelect title="Nível de Risco" text="Todos" />

      <div
        className="
          mt-2
          rounded-xl
          bg-white p-4
        "
      >
        <div
          className="
            flex items-center gap-2
            text-[#006b47]
          "
        >
          <span className="material-symbols-outlined text-[19px]">
            database
          </span>

          <strong className="font-title text-sm">
            Fonte dos dados
          </strong>
        </div>

        <p
          className="
            font-data
            mt-2 text-[10px]
            leading-5
            text-[#49607e]
          "
        >
          Portal Nacional de Contratações
          Públicas (PNCP) e IBGE.
        </p>
      </div>
    </aside>
  );
}


/* =========================================================
   CONTEÚDO PRINCIPAL
========================================================= */

function DashboardContent() {
  return (
    <div
      className="
        flex min-w-0 flex-col gap-5
        p-5 sm:p-7
        lg:col-span-9
      "
    >
      {/* ---------- CABEÇALHO ---------- */}

      <div>
        <h3
          className="
            font-title
            text-2xl font-bold
          "
        >
          Visão Geral
        </h3>

        <p
          className="
            mt-1 text-sm
            text-[#49607e]
          "
        >
          Contratos públicos dos municípios
          do Ceará
        </p>

        <span
          className="
            font-data
            mt-2 inline-block
            rounded-full
            bg-[#8df7c1]/35
            px-2.5 py-1
            text-[10px]
            font-bold
            text-[#005235]
          "
        >
          22.324 contratos analisados
        </span>
      </div>

      {/* ---------- KPIs ---------- */}

      <div
        className="
          grid grid-cols-2
          gap-3
          xl:grid-cols-4
        "
      >
        {KPIS.map((kpi) => (
          <MiniKpi
            key={kpi.label}
            label={kpi.label}
            value={kpi.value}
          />
        ))}
      </div>

      {/* ---------- MAPA + CATEGORIAS ---------- */}

      <div
        className="
          grid grid-cols-1
          gap-4
          xl:grid-cols-5
        "
      >
        <MapaCard />

        <CategoriasCard />
      </div>

      {/* ---------- RANKING DE RISCO ---------- */}

      <RiscoCard />
    </div>
  );
}


/* ---------------------------------------------------------
   MAPA
--------------------------------------------------------- */

function MapaCard() {
  return (
    <div
      className="
        flex flex-col gap-3
        rounded-xl
        bg-[#f2f3ff]
        p-5
        xl:col-span-3
      "
    >
      <CardHeader
        title="Distribuição Territorial"
        subtitle="Valor contratado por município · clique para filtrar"
        tag="D3.js"
      />

      <div className="relative">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/mapa-ceara-preview.svg"
          alt="Mapa do Ceará colorido pelo valor contratado em cada município"
          className="mx-auto h-auto max-h-[380px] w-full object-contain"
        />

        <div
          className="
            absolute bottom-0 left-0
            w-[190px]
            rounded-xl
            border border-[#d9e2ec]/90
            bg-white/95
            px-3 py-2.5
            shadow-sm
          "
        >
          <div
            className="
              mb-1.5
              text-[8px]
              font-bold
              uppercase
              tracking-[0.08em]
              text-[#49607e]
            "
          >
            Total contratado (escala log)
          </div>

          <div
            className="h-2 rounded-full"
            style={{
              background:
                "linear-gradient(90deg, #d1fae5, #6ee7b7, #10b981, #047857, #064e3b)",
            }}
          />

          <div
            className="
              mt-1 flex
              justify-between
              text-[8px]
              text-[#49607e]
            "
          >
            <span>{LEGENDA_MAPA.min}</span>
            <span>{LEGENDA_MAPA.max}</span>
          </div>
        </div>
      </div>

      <div
        className="
          flex items-center gap-3
          rounded-xl
          bg-white
          p-4
        "
      >
        <div
          className="
            grid h-10 w-10
            shrink-0
            place-items-center
            rounded-xl
            bg-[#8df7c1]/35
            text-lg
          "
        >
          📍
        </div>

        <div>
          <strong className="text-sm">
            Selecione um município
          </strong>

          <p className="mt-0.5 text-[11px] leading-4 text-[#49607e]">
            Clique no mapa para filtrar o dashboard pelo município e ver
            população, valor contratado e o resumo estatístico dos contratos.
          </p>
        </div>
      </div>
    </div>
  );
}


/* ---------------------------------------------------------
   CATEGORIAS
--------------------------------------------------------- */

function CategoriasCard() {
  return (
    <div
      className="
        rounded-xl
        bg-[#f2f3ff]
        p-5
        xl:col-span-2
      "
    >
      <strong className="font-title">
        Categorias
      </strong>

      <p
        className="
          font-data
          mt-1 text-[10px]
          text-[#49607e]
        "
      >
        Distribuição do valor contratado
      </p>

      <div className="mt-6 space-y-5">
        {CATEGORIAS.map((categoria) => (
          <Bar
            key={categoria.nome}
            title={`${categoria.nome} · ${categoria.fatia}%`}
            width={`${categoria.largura}%`}
          />
        ))}
      </div>
    </div>
  );
}


/* ---------------------------------------------------------
   CONTRATOS COM MAIOR RISCO
--------------------------------------------------------- */

function RiscoCard() {
  const colunas = [
    "Município",
    "Esfera",
    "Categoria",
    "Valor (R$)",
    "Índice de risco",
    "Motivo",
  ];

  return (
    <div
      className="
        flex flex-col gap-4
        rounded-xl
        bg-[#f2f3ff]
        p-5
      "
    >
      <CardHeader
        title="Contratos com Maior Risco"
        subtitle="Apontados pelo Isolation Forest, do mais atípico ao menos atípico"
        tag="Isolation Forest"
        tagClassName="bg-[#fbbc2c]/30 text-[#8a5a00]"
      />

      <div
        className="
          overflow-x-auto
          rounded-lg
          border border-[#e2e7ff]
          bg-white
        "
      >
        <table className="w-full min-w-[720px] text-left text-[11px]">
          <thead>
            <tr className="border-b border-[#e2e7ff] bg-[#fafbff] text-[#49607e]">
              {colunas.map((coluna) => (
                <th
                  key={coluna}
                  className="whitespace-nowrap px-3 py-2 font-semibold"
                >
                  {coluna}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {TOP_RISCO.map((linha, i) => (
              <tr
                key={`${linha.municipio}-${i}`}
                className="border-b border-[#f0f2ff] last:border-0"
              >
                <td className="whitespace-nowrap px-3 py-2">{linha.municipio}</td>
                <td className="whitespace-nowrap px-3 py-2">{linha.esfera}</td>
                <td className="whitespace-nowrap px-3 py-2">{linha.categoria}</td>
                <td className="font-data whitespace-nowrap px-3 py-2 text-right">{linha.valor}</td>
                <td className="font-data whitespace-nowrap px-3 py-2 text-right">{linha.indice}</td>
                <td className="max-w-[320px] truncate px-3 py-2" title={linha.motivo}>
                  {linha.motivo}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-[10px] text-[#49607e]">
        O índice indica atipicidade estatística em relação aos demais
        contratos, não uma irregularidade comprovada.
      </p>
    </div>
  );
}


/* =========================================================
   COMPONENTES PEQUENOS
========================================================= */

function SidebarTitle({
  icon,
  text,
}: {
  icon: string;
  text: string;
}) {
  return (
    <div
      className="
        flex items-center gap-2
        border-b
        border-[#bdcac0]/45
        pb-3
      "
    >
      <span
        className="
          material-symbols-outlined
          text-[22px]
          text-[#006b47]
        "
      >
        {icon}
      </span>

      <strong className="font-title">{text}</strong>
    </div>
  );
}

function FilterLabel({ text }: { text: string }) {
  return (
    <label className="mb-2 block text-sm font-semibold">
      {text}
    </label>
  );
}

function FakeField({
  text,
  icon,
}: {
  text: string;
  icon: string;
}) {
  return (
    <div
      className="
        flex
        items-center
        justify-between
        gap-2
        rounded-lg
        bg-white
        px-3 py-2.5
        text-xs
        shadow-sm
      "
    >
      <span className="truncate">{text}</span>

      <span
        className="
          material-symbols-outlined
          text-[16px]
          text-[#49607e]
        "
      >
        {icon}
      </span>
    </div>
  );
}

function FakeSelect({
  title,
  text,
}: {
  title: string;
  text: string;
}) {
  return (
    <div>
      <FilterLabel text={title} />
      <FakeField text={text} icon="expand_more" />
    </div>
  );
}

function CardHeader({
  title,
  subtitle,
  tag,
  tagClassName = "bg-[#8df7c1]/45 text-[#005235]",
}: {
  title: string;
  subtitle: string;
  tag: string;
  tagClassName?: string;
}) {
  return (
    <div
      className="
        flex items-start
        justify-between
        gap-3
      "
    >
      <div>
        <strong className="font-title">{title}</strong>

        <p
          className="
            font-data
            mt-1 text-[10px]
            text-[#49607e]
          "
        >
          {subtitle}
        </p>
      </div>

      <span
        className={`
          font-data
          shrink-0
          rounded-md
          px-2 py-1
          text-[9px]
          ${tagClassName}
        `}
      >
        {tag}
      </span>
    </div>
  );
}

function MiniKpi({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div
      className="
        min-w-0
        rounded-xl
        bg-[#f2f3ff]
        p-4
      "
    >
      <span className="text-xs text-[#49607e]">
        {label}
      </span>

      <div
        className="
          font-title
          mt-2 break-words
          text-lg font-bold
          leading-tight
          sm:text-xl
        "
      >
        {value}
      </div>
    </div>
  );
}

function Bar({
  title,
  width,
}: {
  title: string;
  width: string;
}) {
  return (
    <div>
      <div className="mb-2 text-xs">
        {title}
      </div>

      <div
        className="
          h-2 overflow-hidden
          rounded-full
          bg-[#dae2fd]
        "
      >
        <div
          className="
            h-full rounded-full
            bg-[#006b47]
          "
          style={{ width }}
        />
      </div>
    </div>
  );
}