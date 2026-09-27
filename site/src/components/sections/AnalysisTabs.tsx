"use client";

import { useState } from "react";

type Tab =
  | "gastos"
  | "padroes"
  | "temporal"
  | "fornecedores";

export default function AnalysisTabs() {
  const [activeTab, setActiveTab] =
    useState<Tab>("gastos");

  return (
    <section
      className="
        bg-[#f2f3ff]
        pb-20
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
            soft-shadow
            rounded-2xl
            bg-white p-6
          "
        >
          <div
            className="
              flex flex-col
              justify-between
              gap-4
              md:flex-row
              md:items-center
            "
          >
            <div>
              <span
                className="
                  font-data
                  text-[10px]
                  font-bold
                  uppercase
                  tracking-wider
                  text-[#006b47]
                "
              >
                Análises Exploratórias
              </span>

              <h3
                className="
                  font-title
                  mt-1 text-xl
                  font-bold
                "
              >
                Diferentes perspectivas dos dados
              </h3>
            </div>

            <div className="flex flex-wrap gap-2">
              <TabButton
                active={activeTab === "gastos"}
                onClick={() =>
                  setActiveTab("gastos")
                }
              >
                Gastos
              </TabButton>

              <TabButton
                active={activeTab === "padroes"}
                onClick={() =>
                  setActiveTab("padroes")
                }
              >
                Padrões
              </TabButton>

              <TabButton
                active={activeTab === "temporal"}
                onClick={() =>
                  setActiveTab("temporal")
                }
              >
                Temporal
              </TabButton>

              <TabButton
                active={
                  activeTab === "fornecedores"
                }
                onClick={() =>
                  setActiveTab("fornecedores")
                }
              >
                Fornecedores
              </TabButton>
            </div>
          </div>

          <div className="mt-7 min-h-[250px]">
            {activeTab === "gastos" && (
              <GastosTab />
            )}

            {activeTab === "padroes" && (
              <PadroesTab />
            )}

            {activeTab === "temporal" && (
              <TemporalTab />
            )}

            {activeTab === "fornecedores" && (
              <FornecedoresTab />
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        active
          ? `
            rounded-lg
            bg-[#006b47]
            px-4 py-2
            text-sm font-bold
            text-white
          `
          : `
            rounded-lg
            bg-[#eaedff]
            px-4 py-2
            text-sm font-medium
            text-[#3e4942]
            transition
            hover:bg-[#e2e7ff]
          `
      }
    >
      {children}
    </button>
  );
}

function GastosTab() {
  return (
    <div
      className="
        grid grid-cols-1
        gap-5 md:grid-cols-2
      "
    >
      <AnalysisBox
        icon="payments"
        title="Distribuição dos Gastos"
        description="Análise do valor contratado considerando municípios, categorias e períodos."
      />

      <AnalysisBox
        icon="leaderboard"
        title="Ranking de Contratos"
        description="Comparação dos contratos com maiores valores e maiores pontuações indicativas de anomalia."
      />
    </div>
  );
}

function PadroesTab() {
  return (
    <div
      className="
        grid grid-cols-1
        gap-5 md:grid-cols-2
      "
    >
      <AnalysisBox
        icon="warning"
        title="Comportamentos Atípicos"
        description="Contratos que se afastam do comportamento predominante observado na base."
      />

      <AnalysisBox
        icon="psychology"
        title="Isolation Forest"
        description="Modelo não supervisionado utilizado para produzir pontuações de anomalia."
      />
    </div>
  );
}

function TemporalTab() {
  return (
    <div
      className="
        rounded-xl
        bg-[#f2f3ff]
        p-6
      "
    >
      <div
        className="
          flex items-center
          justify-between
        "
      >
        <strong>
          Evolução temporal dos contratos
        </strong>

        <span
          className="
            font-data
            text-[10px]
            font-bold
            text-[#006b47]
          "
        >
          2022 — 2026
        </span>
      </div>

      <svg
        viewBox="0 0 700 160"
        className="
          mt-8 h-40
          w-full
          text-[#006b47]
        "
      >
        <line
          x1="40"
          y1="130"
          x2="680"
          y2="130"
          stroke="currentColor"
          strokeOpacity="0.18"
        />

        <line
          x1="40"
          y1="80"
          x2="680"
          y2="80"
          stroke="currentColor"
          strokeOpacity="0.1"
          strokeDasharray="4 4"
        />

        <line
          x1="40"
          y1="30"
          x2="680"
          y2="30"
          stroke="currentColor"
          strokeOpacity="0.1"
          strokeDasharray="4 4"
        />

        <polyline
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
          points="
            50,115
            130,107
            210,98
            290,82
            370,88
            450,64
            530,55
            610,30
            670,40
          "
        />
      </svg>
    </div>
  );
}

function FornecedoresTab() {
  const fornecedores = [
    ["Fornecedor A", "—", "—"],
    ["Fornecedor B", "—", "—"],
    ["Fornecedor C", "—", "—"],
  ];

  return (
    <div
      className="
        overflow-hidden
        rounded-xl
        border border-[#bdcac0]/30
      "
    >
      <div
        className="
          grid grid-cols-3
          bg-[#eaedff]
          px-4 py-3
          text-sm font-semibold
        "
      >
        <span>Fornecedor</span>
        <span>Contratos</span>
        <span className="text-right">
          Valor
        </span>
      </div>

      {fornecedores.map((row) => (
        <div
          key={row[0]}
          className="
            grid grid-cols-3
            border-t
            border-[#bdcac0]/30
            px-4 py-4
            text-sm
          "
        >
          <span className="font-semibold">
            {row[0]}
          </span>

          <span>{row[1]}</span>

          <span
            className="
              text-right
              font-semibold
              text-[#006b47]
            "
          >
            {row[2]}
          </span>
        </div>
      ))}
    </div>
  );
}

function AnalysisBox({
  icon,
  title,
  description,
}: {
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <div
      className="
        rounded-xl
        bg-[#f2f3ff]
        p-6
      "
    >
      <span
        className="
          material-symbols-outlined
          text-[28px]
          text-[#006b47]
        "
      >
        {icon}
      </span>

      <h4
        className="
          font-title
          mt-4 text-lg
          font-bold
        "
      >
        {title}
      </h4>

      <p
        className="
          mt-2 leading-7
          text-[#3e4942]
        "
      >
        {description}
      </p>
    </div>
  );
}