export default function DashboardPreview() {
  const STREAMLIT_URL =
    process.env.NEXT_PUBLIC_STREAMLIT_URL || "#";

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
              grid min-h-[620px]
              grid-cols-1
              lg:grid-cols-12
            "
          >
            <DashboardSidebar />

            <DashboardContent />
          </div>
        </div>
      </div>
    </section>
  );
}

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

          contratos-ce.streamlit.app
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

function DashboardSidebar() {
  return (
    <aside
      className="
        flex flex-col gap-6
        bg-[#eaedff]/70
        p-5
        lg:col-span-3
      "
    >
      <div
        className="
          flex items-center gap-2
          border-b
          border-[#bdcac0]/40
          pb-4
        "
      >
        <span
          className="
            material-symbols-outlined
            text-[#006b47]
          "
        >
          tune
        </span>

        <strong>Filtros Dinâmicos</strong>
      </div>

      <div>
        <label className="text-sm font-semibold">
          Ano do Contrato
        </label>

        <div
          className="
            mt-2 grid grid-cols-3
            gap-1
            rounded-lg
            bg-[#e2e7ff]
            p-1
          "
        >
          <button
            className="
              font-data
              rounded-md
              bg-[#006b47]
              py-1.5
              text-[10px]
              font-bold
              text-white
            "
          >
            2026
          </button>

          <button
            className="
              font-data
              rounded-md
              py-1.5
              text-[10px]
              hover:bg-white
            "
          >
            2025
          </button>

          <button
            className="
              font-data
              rounded-md
              py-1.5
              text-[10px]
              hover:bg-white
            "
          >
            Todos
          </button>
        </div>
      </div>

      <FakeSelect
        title="Município"
        text="Todos os municípios"
      />

      <FakeSelect
        title="Categoria"
        text="Todas as categorias"
      />

      <FakeSelect
        title="Nível de Risco"
        text="Todos"
      />

      <div
        className="
          mt-auto
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

          <strong className="text-sm">
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

function DashboardContent() {
  return (
    <div
      className="
        flex flex-col gap-6
        p-5 sm:p-7
        lg:col-span-9
      "
    >
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
      </div>

      <div
        className="
          grid grid-cols-2
          gap-3
          lg:grid-cols-4
        "
      >
        <MiniKpi label="Contratos" value="—" />
        <MiniKpi label="Valor Total" value="—" />
        <MiniKpi label="Municípios" value="184" />
        <MiniKpi label="Anomalias" value="—" />
      </div>

      <div
        className="
          grid grid-cols-1
          gap-4
          xl:grid-cols-5
        "
      >
        <div
          className="
            flex min-h-[270px]
            flex-col
            rounded-xl
            bg-[#f2f3ff]
            p-5
            xl:col-span-3
          "
        >
          <div
            className="
              flex items-center
              justify-between
            "
          >
            <div>
              <strong>
                Distribuição Territorial
              </strong>

              <p
                className="
                  font-data
                  mt-1 text-[10px]
                  text-[#49607e]
                "
              >
                Valor contratado por município
              </p>
            </div>

            <span
              className="
                font-data
                rounded-md
                bg-[#8df7c1]/40
                px-2 py-1
                text-[9px]
                text-[#005235]
              "
            >
              D3.js
            </span>
          </div>

          <div
            className="
              flex flex-1
              items-center justify-center
            "
          >
            <div className="text-center">
              <span
                className="
                  material-symbols-outlined
                  text-[86px]
                  text-[#006b47]/80
                "
              >
                map
              </span>

              <p
                className="
                  font-title
                  mt-2 font-bold
                "
              >
                Mapa do Ceará
              </p>

              <p
                className="
                  font-data
                  mt-1 text-[10px]
                  text-[#49607e]
                "
              >
                D3.js + GeoJSON
              </p>
            </div>
          </div>
        </div>

        <div
          className="
            rounded-xl
            bg-[#f2f3ff]
            p-5
            xl:col-span-2
          "
        >
          <strong>Categorias</strong>

          <p
            className="
              font-data
              mt-1 text-[10px]
              text-[#49607e]
            "
          >
            Distribuição ilustrativa
          </p>

          <div className="mt-7 space-y-5">
            <FakeBar title="Serviços" width="82%" />
            <FakeBar title="Aquisições" width="68%" />
            <FakeBar title="Obras" width="49%" />
            <FakeBar title="Outros" width="31%" />
          </div>
        </div>
      </div>

      <div
        className="
          rounded-xl
          bg-[#eaedff]/60
          p-4
        "
      >
        <div className="flex items-center gap-2">
          <span
            className="
              material-symbols-outlined
              text-[#006b47]
            "
          >
            insights
          </span>

          <span className="text-sm">
            Visualização demonstrativa da
            aplicação Streamlit.
          </span>
        </div>
      </div>
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
      <label className="text-sm font-semibold">
        {title}
      </label>

      <div
        className="
          mt-2 flex
          items-center
          justify-between
          rounded-lg
          bg-white
          px-3 py-2.5
          text-xs
          shadow-sm
        "
      >
        {text}

        <span
          className="
            material-symbols-outlined
            text-[16px]
            text-[#49607e]
          "
        >
          expand_more
        </span>
      </div>
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
          mt-2 text-2xl
          font-bold
        "
      >
        {value}
      </div>
    </div>
  );
}

function FakeBar({
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