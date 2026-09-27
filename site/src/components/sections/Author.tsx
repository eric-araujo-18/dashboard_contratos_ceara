export default function Author() {
  return (
    <section
      id="autor"
      className="bg-white py-20"
    >
      <div
        className="
          mx-auto max-w-7xl
          px-6 lg:px-12
        "
      >
        <div className="mb-10">
          <span
            className="
              font-data
              text-[11px]
              font-bold uppercase
              tracking-wider
              text-[#006b47]
            "
          >
            Corpo Acadêmico
          </span>

          <h2
            className="
              font-title
              mt-2 text-3xl
              font-bold
              md:text-4xl
            "
          >
            Sobre o Autor e o Projeto de Pesquisa
          </h2>
        </div>

        <div
          className="
            grid grid-cols-1
            gap-8
            lg:grid-cols-12
          "
        >
          <div
            className="
              rounded-2xl
              bg-[#f2f3ff]
              p-6
              lg:col-span-4
            "
          >
            <div className="flex items-center gap-4">
              <div
                className="
                  font-title
                  flex h-16 w-16
                  items-center justify-center
                  rounded-full
                  bg-[#006b47]
                  text-xl font-bold
                  text-white
                "
              >
                EA
              </div>

              <div>
                <h3
                  className="
                    font-title
                    text-lg font-bold
                  "
                >
                  Eric de Araújo Albuquerque
                </h3>

                <p
                  className="
                    font-data
                    mt-1 text-[10px]
                    text-[#49607e]
                  "
                >
                  Ciência da Computação
                </p>

                <p
                  className="
                    font-data
                    mt-1 text-[10px]
                    font-semibold
                    text-[#006b47]
                  "
                >
                  Universidade Federal do Ceará
                </p>
              </div>
            </div>

            <p
              className="
                mt-6 leading-7
                text-[#3e4942]
              "
            >
              Trabalho voltado à aplicação de
              Ciência de Dados, visualização
              interativa e aprendizado de
              máquina na análise de contratos
              públicos dos municípios cearenses.
            </p>

            <div className="mt-6 space-y-2">
              <ExternalButton
                icon="code"
                text="Perfil no GitHub"
                href="https://github.com"
              />

              <ExternalButton
                icon="badge"
                text="LinkedIn"
                href="https://linkedin.com"
              />
            </div>
          </div>

          <div
            className="
              flex flex-col gap-5
              lg:col-span-8
            "
          >
            <div
              className="
                rounded-2xl
                bg-[#f2f3ff]
                p-7
              "
            >
              <span
                className="
                  font-data
                  text-[10px]
                  text-[#49607e]
                "
              >
                Título da Pesquisa
              </span>

              <h3
                className="
                  font-title
                  mt-2 text-xl
                  font-bold
                "
              >
                Proposta de Plataforma para
                Visualização e Detecção de
                Anomalias de Contratos Públicos
                usando Aprendizado de Máquina
              </h3>
            </div>

            <div
              className="
                grid grid-cols-1
                gap-4
                sm:grid-cols-2
              "
            >
              <AcademicCard
                title="Orientador"
                value="Prof. Dr. Jose Wellington Franco da Silva"
                description="Universidade Federal do Ceará"
              />

              <AcademicCard
                title="Coorientador"
                value="Prof. Dr. Renan Gomes Vieira"
                description="Universidade Federal do Ceará"
              />

              <AcademicCard
                title="Artefatos Produzidos"
                value="Monografia + Plataforma"
                description="Código e dashboard interativo"
              />

              <AcademicCard
                title="Área"
                value="Ciência de Dados"
                description="Aprendizado de máquina e transparência pública"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ExternalButton({
  icon,
  text,
  href,
}: {
  icon: string;
  text: string;
  href: string;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="
        flex items-center
        justify-between
        rounded-xl
        bg-white p-3
        text-sm
        transition
        hover:bg-[#e2e7ff]
      "
    >
      <span className="flex items-center gap-2">
        <span className="material-symbols-outlined text-[18px]">
          {icon}
        </span>

        {text}
      </span>

      <span
        className="
          material-symbols-outlined
          text-[16px]
          text-[#49607e]
        "
      >
        arrow_forward
      </span>
    </a>
  );
}

function AcademicCard({
  title,
  value,
  description,
}: {
  title: string;
  value: string;
  description: string;
}) {
  return (
    <div
      className="
        rounded-xl
        bg-[#f2f3ff]
        p-5
      "
    >
      <span
        className="
          font-data
          text-[10px]
          text-[#49607e]
        "
      >
        {title}
      </span>

      <div
        className="
          mt-2 font-semibold
        "
      >
        {value}
      </div>

      <div
        className="
          mt-1 text-sm
          text-[#3e4942]
        "
      >
        {description}
      </div>
    </div>
  );
}