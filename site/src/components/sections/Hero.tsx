import KpiCard from "../ui/KpiCard";
import MetadataItem from "../ui/MetadataItem";

const STREAMLIT_URL =
  process.env.NEXT_PUBLIC_STREAMLIT_URL || "#";

export default function Hero() {
  return (
    <section
      id="sobre"
      className="
        hero-grid
        relative overflow-hidden
        pb-16 pt-10
        lg:pb-24
      "
    >
      {/* Decoração */}
      <div
        className="
          pointer-events-none
          absolute -right-[5%]
          -top-32 -z-10
          h-[620px] w-[620px]
          rounded-full
          bg-[#c4dcff]/40
          blur-3xl
        "
      />


      <div
        className="
          mx-auto flex max-w-7xl
          flex-col gap-10
          px-6 lg:px-12
        "
      >
        {/* Badges */}
        <div className="flex flex-wrap items-center gap-3">
          <span
            className="
              font-data
              inline-flex items-center gap-2
              rounded-full
              bg-[#e2e7ff]
              px-3.5 py-1.5
              text-[11px]
              font-semibold
              shadow-sm
            "
          >
            <span
              className="
                material-symbols-outlined
                text-[16px]
                text-[#006b47]
              "
            >
              school
            </span>

            Trabalho de Conclusão de Curso
            • Ciência da Computação
          </span>

          <span
            className="
              font-data
              inline-flex items-center gap-1.5
              rounded-full
              bg-[#8df7c1]/40
              px-3 py-1
              text-[11px]
              font-medium
              text-[#005235]
            "
          >
            <span
              className="
                h-1.5 w-1.5
                rounded-full
                bg-[#006b47]
              "
            />

            Transparência Pública
          </span>
        </div>

        <div
          className="
            grid grid-cols-1
            items-start gap-8
            lg:grid-cols-12
          "
        >
          {/* Conteúdo principal */}
          <div
            className="
              flex flex-col gap-6
              lg:col-span-8
            "
          >
            <h1
              className="
                font-title
                max-w-5xl
                text-4xl
                font-extrabold
                leading-[1.05]
                tracking-tight
                sm:text-5xl
                xl:text-[64px]
              "
            >
              Transparência e Inteligência em{" "}

              <span
                className="
                  text-[#006b47]
                  underline
                  decoration-[#fbbc2c]/70
                  decoration-4
                  underline-offset-8
                "
              >
                Contratos Públicos
              </span>{" "}

              do Ceará
            </h1>

            <p
              className="
                max-w-3xl
                text-lg leading-8
                text-[#3e4942]
              "
            >
              Plataforma interativa para
              visualização, análise e
              identificação de comportamentos
              atípicos em contratos públicos
              dos municípios do Ceará,
              combinando dados abertos,
              estatística e aprendizado de
              máquina.
            </p>

            <div
              className="
                flex flex-col gap-4
                pt-2 sm:flex-row
              "
            >
              <a
                href={STREAMLIT_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="
                  group inline-flex
                  items-center justify-center
                  gap-3
                  rounded-xl
                  bg-[#00875a]
                  px-7 py-4
                  font-semibold
                  text-white
                  shadow-md
                  transition
                  hover:bg-[#006b47]
                "
              >
                <span className="material-symbols-outlined text-[24px]">
                  rocket_launch
                </span>

                Acessar Dashboard no Streamlit

                <span
                  className="
                    material-symbols-outlined
                    text-[18px]
                    transition-transform
                    group-hover:translate-x-1
                  "
                >
                  arrow_forward
                </span>
              </a>

              <a
                href="#metodologia"
                className="
                  inline-flex
                  items-center justify-center
                  gap-2
                  rounded-xl
                  bg-[#eaedff]
                  px-6 py-4
                  font-semibold
                  shadow-sm
                  transition
                  hover:bg-[#e2e7ff]
                "
              >
                <span
                  className="
                    material-symbols-outlined
                    text-[#49607e]
                  "
                >
                  description
                </span>

                Metodologia do Projeto
              </a>
            </div>

            <div
              className="
                font-data
                flex items-center gap-2
                text-[11px]
                text-[#3e4942]
              "
            >
              <span
                className="
                  material-symbols-outlined
                  text-[18px]
                  text-[#006b47]
                "
              >
                bolt
              </span>

              Dashboard interativo hospedado no
              Streamlit Cloud • PNCP + IBGE
            </div>
          </div>

          {/* Metadados */}
          <aside
            className="
              soft-shadow
              flex flex-col gap-4
              rounded-2xl
              bg-white p-6
              lg:col-span-4
            "
          >
            <div
              className="
                flex items-center
                justify-between
                border-b
                border-[#bdcac0]/30
                pb-3
              "
            >
              <span
                className="
                  font-data
                  text-[11px]
                  uppercase
                  tracking-wider
                  text-[#49607e]
                "
              >
                Metadados Acadêmicos
              </span>

              <span
                className="
                  h-2.5 w-2.5
                  rounded-full
                  bg-[#006b47]
                "
              />
            </div>

            <MetadataItem
              label="Instituição / Campus"
              value="Universidade Federal do Ceará • Campus Crateús"
            />

            <MetadataItem
              label="Curso"
              value="Ciência da Computação"
            />

            <MetadataItem
              label="Área de Pesquisa"
              value="Ciência de Dados & Aprendizado de Máquina"
            />

            <MetadataItem
              label="Fontes Primárias"
              value="PNCP • IBGE"
            />

            <div
              className="
                flex items-center
                justify-between
                border-t
                border-[#bdcac0]/30
                pt-4
              "
            >
              <span
                className="
                  font-data
                  text-[11px]
                  text-[#49607e]
                "
              >
                Projeto
              </span>

              <span
                className="
                  font-data
                  rounded-md
                  bg-[#eaedff]
                  px-2.5 py-1
                  text-[11px]
                  font-bold
                "
              >
                TCC 2026
              </span>
            </div>
          </aside>
        </div>

        {/* KPIs */}
        <div
          className="
            grid grid-cols-1
            gap-4
            sm:grid-cols-2
            lg:grid-cols-4
          "
        >
          <KpiCard
            title="Volume Financeiro"
            icon="payments"
            value="—"
            description="Valor processado pela plataforma"
            color="#006b47"
          />

          <KpiCard
            title="Abrangência Territorial"
            icon="map"
            value="184"
            description="Municípios do Ceará"
            color="#7a5800"
          />

          <KpiCard
            title="Contratos Analisados"
            icon="description"
            value="—"
            description="Registros obtidos do PNCP"
            color="#49607e"
          />

          <KpiCard
            title="Detecção de Anomalias"
            icon="psychology"
            value="ML"
            description="Aprendizado não supervisionado"
            color="#006b47"
          />
        </div>
      </div>
    </section>
  );
}