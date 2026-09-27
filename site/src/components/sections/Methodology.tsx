import PipelineCard from "../ui/PipelineCard";

export default function Methodology() {
  const technologies = [
    "Python",
    "Streamlit",
    "Pandas",
    "NumPy",
    "Scikit-learn",
    "Isolation Forest",
    "D3.js",
    "GeoJSON",
    "Next.js",
    "Tailwind CSS",
    "Vercel",
  ];

  return (
    <section
      id="metodologia"
      className="bg-[#f2f3ff] py-20"
    >
      <div
        className="
          mx-auto flex max-w-7xl
          flex-col gap-12
          px-6 lg:px-12
        "
      >
        <div>
          <span
            className="
              font-data
              text-[11px]
              font-bold uppercase
              tracking-wider
              text-[#006b47]
            "
          >
            Arquitetura de Dados
          </span>

          <h2
            className="
              font-title
              mt-2 text-3xl
              font-bold
              md:text-4xl
            "
          >
            Pipeline Tecnológico & Metodologia
          </h2>

          <p
            className="
              mt-3 max-w-2xl
              leading-7
              text-[#3e4942]
            "
          >
            Fluxo de processamento desde a
            coleta dos dados públicos até a
            classificação e apresentação dos
            resultados no dashboard.
          </p>
        </div>

        <div
          className="
            grid grid-cols-1
            gap-6
            sm:grid-cols-2
            lg:grid-cols-4
          "
        >
          <PipelineCard
            code="01 • ETL"
            icon="cloud_download"
            title="Extração"
            description="Coleta automatizada de contratos públicos disponibilizados pelo Portal Nacional de Contratações Públicas."
            tech="PNCP • API REST • JSON"
          />

          <PipelineCard
            code="02 • DATA ENG"
            icon="cleaning_services"
            title="Tratamento & Normalização"
            description="Tratamento de valores ausentes, padronização de campos, conversão de tipos e enriquecimento dos registros."
            tech="Pandas • NumPy • Python"
          />

          <PipelineCard
            code="03 • ML"
            icon="psychology"
            title="Análise & Modelagem"
            description="Análise estatística, construção de atributos e aplicação de técnicas de aprendizado de máquina não supervisionado."
            tech="Scikit-learn • Isolation Forest"
          />

          <PipelineCard
            code="04 • DEPLOY"
            icon="rocket"
            title="Visualização Cívica"
            description="Apresentação dos indicadores, filtros, mapas e níveis indicativos de anomalia em uma aplicação interativa."
            tech="Streamlit • D3.js • GeoJSON"
            active
          />
        </div>

        <div
          className="
            flex flex-col
            justify-between gap-5
            rounded-2xl
            bg-[#eaedff]
            p-6
            lg:flex-row
            lg:items-center
          "
        >
          <div className="flex items-center gap-3">
            <span
              className="
                material-symbols-outlined
                text-[#006b47]
              "
            >
              code_blocks
            </span>

            <strong
              className="
                font-title text-lg
              "
            >
              Stack Tecnológica Utilizada
            </strong>
          </div>

          <div className="flex flex-wrap gap-2">
            {technologies.map((tech) => (
              <span
                key={tech}
                className="
                  font-data
                  rounded-md
                  bg-white
                  px-3 py-1.5
                  text-[10px]
                  font-semibold
                  shadow-sm
                "
              >
                {tech}
              </span>
            ))}
          </div>
        </div>

        <CallToAction />
      </div>
    </section>
  );
}

function CallToAction() {
  const STREAMLIT_URL =
    process.env.NEXT_PUBLIC_STREAMLIT_URL || "#";

  return (
    <div
      className="
        relative overflow-hidden
        rounded-3xl
        bg-[#283044]
        p-8 text-[#eef0ff]
        shadow-xl
        sm:p-12
        lg:flex
        lg:items-center
        lg:justify-between
        lg:p-16
      "
    >
      <div
        className="
          pointer-events-none
          absolute
          -bottom-20 -right-20
          h-80 w-80
          rounded-full
          bg-[#006b47]/30
          blur-3xl
        "
      />

      <div className="relative z-10 max-w-2xl">
        <span
          className="
            font-data
            inline-flex
            items-center gap-2
            text-[11px]
            font-semibold
            uppercase
            tracking-wider
            text-[#8df7c1]
          "
        >
          <span
            className="
              pulse-dot
              h-2 w-2
              rounded-full
              bg-[#8df7c1]
            "
          />

          Acesso público
        </span>

        <h2
          className="
            font-title
            mt-4 text-3xl
            font-bold
            md:text-4xl
          "
        >
          Explore os contratos públicos dos
          municípios do Ceará
        </h2>

        <p
          className="
            mt-4 max-w-xl
            leading-7
            text-[#dae2fd]
          "
        >
          Utilize filtros, indicadores,
          mapas e análises para explorar os
          dados e compreender os resultados.
        </p>
      </div>

      <a
        href={STREAMLIT_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="
          relative z-10
          mt-8
          inline-flex
          items-center justify-center
          gap-3
          rounded-xl
          bg-[#8df7c1]
          px-8 py-5
          font-bold
          text-[#002113]
          shadow-lg
          transition
          hover:bg-[#71dba6]
          lg:mt-0
        "
      >
        <span className="material-symbols-outlined">
          rocket_launch
        </span>

        Lançar Aplicação Streamlit

        <span className="material-symbols-outlined">
          open_in_new
        </span>
      </a>
    </div>
  );
}