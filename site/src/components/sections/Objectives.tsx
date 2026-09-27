import ObjectiveCard from "../ui/ObjectiveCard";

export default function Objectives() {
  return (
    <section
      id="objetivos"
      className="
        mx-auto flex max-w-7xl
        flex-col gap-12
        px-6 py-20
        lg:px-12
      "
    >
      <div className="flex flex-col gap-3">
        <span
          className="
            font-data
            text-[11px]
            font-bold uppercase
            tracking-wider
            text-[#006b47]
          "
        >
          Fundamentação Acadêmica
        </span>

        <h2
          className="
            font-title
            text-3xl font-bold
            md:text-4xl
          "
        >
          Objetivos do Trabalho de
          Conclusão de Curso
        </h2>

        <p
          className="
            max-w-3xl
            text-lg leading-8
            text-[#3e4942]
          "
        >
          A pesquisa propõe uma plataforma
          capaz de organizar, contextualizar
          e visualizar dados de contratos
          públicos, apoiando a identificação
          de comportamentos atípicos e o
          controle social.
        </p>
      </div>

      <div
        className="
          grid grid-cols-1
          gap-6 md:grid-cols-3
        "
      >
        <ObjectiveCard
          icon="visibility"
          number="Pilar 01"
          title="Acessibilidade da Informação"
          description="Transformar dados contratuais extensos e complexos em informações visuais mais acessíveis e compreensíveis."
          footer="Transparência Ativa"
          color="green"
        />

        <ObjectiveCard
          icon="policy"
          number="Pilar 02"
          title="Controle Social"
          description="Oferecer ferramentas que auxiliem a exploração de contratos e destaquem registros que mereçam análise posterior."
          footer="Fiscalização Democrática"
          color="blue"
        />

        <ObjectiveCard
          icon="data_exploration"
          number="Pilar 03"
          title="Ciência de Dados Aplicada"
          description="Empregar análise estatística e aprendizado de máquina não supervisionado para identificar comportamentos atípicos."
          footer="Rigor Metodológico"
          color="yellow"
        />
      </div>
    </section>
  );
}