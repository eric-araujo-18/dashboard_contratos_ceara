import FooterLink from "../ui/FooterLink";

const STREAMLIT_URL =
  process.env.NEXT_PUBLIC_STREAMLIT_URL || "#";

export default function Footer() {
  return (
    <footer
      className="
        bg-[#f2f3ff]
        pt-14
      "
    >
      <div
        className="
          mx-auto max-w-7xl
          px-6 lg:px-12
        "
      >
        <div
          className="
            grid grid-cols-1
            gap-10
            md:grid-cols-4
          "
        >
          <div
            className="
              space-y-4
              md:col-span-2
            "
          >
            <div className="flex items-center gap-3">
              <div
                className="
                  flex h-9 w-9
                  items-center justify-center
                  rounded-lg
                  bg-[#006b47]
                  text-white
                "
              >
                <span className="material-symbols-outlined text-[20px]">
                  account_balance
                </span>
              </div>

              <strong
                className="
                  font-title text-lg
                "
              >
                ContratosCE
              </strong>
            </div>

            <p
              className="
                max-w-xl
                text-sm leading-6
                text-[#3e4942]
              "
            >
              Trabalho de Conclusão de Curso
              em Ciência da Computação voltado
              à visualização e detecção de
              comportamentos atípicos em
              contratos públicos dos
              municípios do Ceará.
            </p>

            <div className="flex flex-wrap gap-2">
              <Badge
                icon="database"
                text="PNCP"
              />

              <Badge
                icon="public"
                text="IBGE"
              />

              <Badge
                icon="verified"
                text="Dados Públicos"
              />
            </div>
          </div>

          <div>
            <strong
              className="
                font-data
                text-[11px]
                uppercase
                tracking-wider
              "
            >
              Supervisão Acadêmica
            </strong>

            <div
              className="
                mt-4 space-y-3
                text-sm
                text-[#3e4942]
              "
            >
              <p>
                <strong>Universidade</strong>
                <br />
                Universidade Federal do Ceará
              </p>

              <p>
                <strong>Campus</strong>
                <br />
                Crateús
              </p>

              <p>
                <strong>Curso</strong>
                <br />
                Ciência da Computação
              </p>
            </div>
          </div>

          <div>
            <strong
              className="
                font-data
                text-[11px]
                uppercase
                tracking-wider
              "
            >
              Acesso & Repositórios
            </strong>

            <div
              className="
                mt-4 flex
                flex-col gap-3
              "
            >
              <FooterLink
                icon="code"
                text="Código no GitHub"
                href="https://github.com"
              />

              <FooterLink
                icon="analytics"
                text="Dashboard Streamlit"
                href={STREAMLIT_URL}
              />

              <FooterLink
                icon="database"
                text="Portal PNCP"
                href="https://www.gov.br/pncp"
              />
            </div>
          </div>
        </div>

        <div
          className="
            mt-10
            flex flex-col
            justify-between
            gap-3
            rounded-t-xl
            bg-[#eaedff]/70
            px-6 py-5
            text-sm
            text-[#3e4942]
            sm:flex-row
          "
        >
          <p>
            © 2026 ContratosCE • Trabalho de
            Conclusão de Curso
          </p>

          <p
            className="
              font-data
              text-[10px]
              text-[#49607e]
            "
          >
            Ceará • Brasil
          </p>
        </div>
      </div>
    </footer>
  );
}

function Badge({
  icon,
  text,
}: {
  icon: string;
  text: string;
}) {
  return (
    <span
      className="
        font-data
        inline-flex
        items-center gap-1
        rounded-md
        bg-[#eaedff]
        px-2.5 py-1
        text-[10px]
        text-[#49607e]
      "
    >
      <span className="material-symbols-outlined text-[14px]">
        {icon}
      </span>

      {text}
    </span>
  );
}