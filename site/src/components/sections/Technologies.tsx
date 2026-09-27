const technologies = [
  {
    name: "Python",
    description:
      "Processamento e aprendizado de máquina",
  },

  {
    name: "Streamlit",
    description:
      "Dashboard analítico",
  },

  {
    name: "Pandas",
    description:
      "Manipulação dos dados",
  },

  {
    name: "Scikit-learn",
    description:
      "Modelos de Machine Learning",
  },

  {
    name: "D3.js",
    description:
      "Visualizações geográficas",
  },

  {
    name: "GeoJSON",
    description:
      "Geometrias dos municípios",
  },

  {
    name: "Next.js",
    description:
      "Site institucional",
  },

  {
    name: "Tailwind CSS",
    description:
      "Interface visual",
  },
];


export default function Technologies() {
  return (
    <section
      className="
        mx-auto max-w-7xl
        px-6 py-20
        lg:px-12
      "
    >
      <span
        className="
          font-[var(--font-mono)]
          text-xs font-bold
          uppercase
          tracking-wider
          text-[var(--primary)]
        "
      >
        Tecnologias
      </span>

      <h2
        className="
          mt-2
          font-[var(--font-title)]
          text-3xl font-bold
        "
      >
        Tecnologias utilizadas
      </h2>


      <div
        className="
          mt-10 grid
          grid-cols-2
          gap-4
          md:grid-cols-4
        "
      >
        {technologies.map(
          (technology) => (
            <article
              key={technology.name}
              className="
                rounded-2xl
                bg-white
                p-5
                shadow-sm
              "
            >
              <h3
                className="
                  font-[var(--font-title)]
                  font-bold
                  text-[var(--primary)]
                "
              >
                {technology.name}
              </h3>

              <p
                className="
                  mt-2 text-sm
                  text-[var(--on-surface-variant)]
                "
              >
                {technology.description}
              </p>
            </article>
          )
        )}
      </div>
    </section>
  );
}