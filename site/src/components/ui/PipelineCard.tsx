interface PipelineCardProps {
  code: string;
  icon: string;
  title: string;
  description: string;
  tech: string;
  active?: boolean;
}

export default function PipelineCard({
  code,
  icon,
  title,
  description,
  tech,
  active = false,
}: PipelineCardProps) {
  return (
    <article
      className="
        soft-shadow card-hover
        flex min-h-[300px]
        flex-col justify-between
        rounded-2xl
        bg-white p-6
      "
    >
      <div>
        <div
          className="
            flex items-center
            justify-between
          "
        >
          <span
            className={`
              font-data
              rounded-md
              px-2.5 py-1
              text-[10px]
              font-bold

              ${
                active
                  ? "bg-[#8df7c1]/40 text-[#005235]"
                  : "bg-[#eaedff] text-[#49607e]"
              }
            `}
          >
            {code}
          </span>

          <span
            className="
              material-symbols-outlined
              text-[21px]
              text-[#006b47]
            "
          >
            {icon}
          </span>
        </div>

        <h4
          className="
            font-title
            mt-7 text-lg
            font-bold
          "
        >
          {title}
        </h4>

        <p
          className="
            mt-3 text-sm
            leading-6
            text-[#3e4942]
          "
        >
          {description}
        </p>
      </div>

      <div
        className="
          font-data
          mt-5 text-[10px]
          font-semibold
          text-[#006b47]
        "
      >
        {tech}
      </div>
    </article>
  );
}