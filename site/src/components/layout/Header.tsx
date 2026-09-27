"use client";

import { useActiveSection } from "../../hooks/useActiveSection";

const STREAMLIT_URL =
  process.env.NEXT_PUBLIC_STREAMLIT_URL || "#";

const navigation = [
  { id: "sobre", label: "Sobre" },
  { id: "objetivos", label: "Objetivos" },
  { id: "analises", label: "Análises" },
  { id: "metodologia", label: "Metodologia" },
  { id: "autor", label: "Autor" },
];

export default function Header() {
  const activeSection = useActiveSection(
    navigation.map((item) => item.id)
  );

  return (
    <header
      className="
        fixed inset-x-0 top-0 z-50
        border-b border-[#bdcac0]/30
        bg-[#faf8ff]/90
        backdrop-blur-xl
      "
    >
      <div
        className="
          mx-auto flex h-20 max-w-7xl
          items-center justify-between
          gap-4 px-6 lg:px-12
        "
      >
        {/* LOGO */}
        <a
          href="#sobre"
          className="
            group flex items-center gap-3
          "
        >
          <div
            className="
              flex h-10 w-10
              items-center justify-center
              rounded-xl
              bg-[#006b47]
              text-white
              shadow-sm
              transition-transform
              duration-200
              group-hover:scale-105
            "
          >
            <span
              className="
                material-symbols-outlined
                text-[22px]
              "
            >
              account_balance
            </span>
          </div>

          <div className="flex flex-col">
            <span
              className="
                font-title
                text-xl font-bold
                leading-none
                tracking-tight
                text-[#131b2e]
              "
            >
              ContratosCE
            </span>

            <span
              className="
                font-data
                mt-1 text-[10px]
                uppercase
                tracking-[0.18em]
                text-[#49607e]
              "
            >
              Painel Cívico • TCC
            </span>
          </div>
        </a>

        {/* NAVBAR */}
        <nav
          className="
            hidden items-center gap-1
            xl:flex
          "
        >
          {navigation.map((item) => {
            const isActive =
              activeSection === item.id;

            return (
              <a
                key={item.id}
                href={`#${item.id}`}
                className={`
                  relative
                  rounded-lg
                  px-3 py-2
                  text-sm
                  transition-all
                  duration-200

                  ${
                    isActive
                      ? `
                        bg-[#8df7c1]/30
                        font-semibold
                        // text-[#006b47]
                      `
                      : `
                        text-[#3e4942]
                        hover:bg-[#eaedff]
                        hover:text-[#006b47]
                      `
                  }
                `}
              >
                {item.label}

                {isActive && (
                  <span
                    className="
                      absolute
                      -translate-x-1/2
                      rounded-full
                      bg-[#006b47]
                    "
                  />
                )}
              </a>
            );
          })}
        </nav>

        {/* AÇÕES À DIREITA */}
        <div
          className="
            flex items-center gap-3
          "
        >
          {/* STATUS */}
          <div
            className="
              hidden items-center gap-2
              rounded-lg
              border border-[#8df7c1]/60
              bg-[#8df7c1]/20
              px-3 py-2
              lg:flex
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

            <span
              className="
                font-data
                text-[9px]
                font-semibold
                uppercase
                tracking-widest
                text-[#005235]
              "
            >
              Sistema disponível
            </span>
          </div>

          {/* BOTÃO STREAMLIT */}
          <a
            href={STREAMLIT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="
              group
              hidden items-center gap-3
              rounded-xl
              bg-[#00875a]
              px-4 py-2.5
              text-white
              shadow-sm
              transition-all
              duration-200
              hover:-translate-y-0.5
              hover:bg-[#006b47]
              hover:shadow-md
              sm:flex
            "
          >
            <span
              className="
                material-symbols-outlined
                text-[19px]
              "
            >
              analytics
            </span>

            <span
              className="
                text-sm
                font-semibold
              "
            >
              Dashboard
            </span>

            <span
              className="
                material-symbols-outlined
                text-[16px]
                transition-transform
                group-hover:translate-x-0.5
              "
            >
              open_in_new
            </span>
          </a>

          {/* AVATAR */}
          <div
            className="
              hidden h-9 w-9
              items-center justify-center
              rounded-full
              border border-[#bdcac0]/50
              bg-white
              text-[#006b47]
              shadow-sm
              sm:flex
            "
          >
            <span
              className="
                material-symbols-outlined
                text-[20px]
              "
            >
              person
            </span>
          </div>

          {/* BOTÃO MOBILE */}
          <a
            href={STREAMLIT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="
              flex h-10 w-10
              items-center justify-center
              rounded-xl
              bg-[#006b47]
              text-white
              shadow-sm
              sm:hidden
            "
            aria-label="Abrir Dashboard"
          >
            <span
              className="
                material-symbols-outlined
                text-[20px]
              "
            >
              analytics
            </span>
          </a>
        </div>
      </div>
    </header>
  );
}