interface ObjectiveCardProps {
  icon: string;
  number: string;
  title: string;
  description: string;
  footer: string;
  color: "green" | "blue" | "yellow";
}

export default function ObjectiveCard({
  icon,
  number,
  title,
  description,
  footer,
  color,
}: ObjectiveCardProps) {
  const colorClass =
    color === "green"
      ? "bg-[#8df7c1]/40 text-[#006b47]"
      : color === "blue"
        ? "bg-[#c4dcff]/60 text-[#49607e]"
        : "bg-[#ffdea4]/60 text-[#7a5800]";

  return (
    <article
      className="
        card-hover soft-shadow
        flex min-h-[340px]
        flex-col justify-between
        rounded-2xl
        bg-white p-8
      "
    >
      <div>
        <div
          className={`
            flex h-12 w-12
            items-center justify-center
            rounded-xl
            ${colorClass}
          `}
        >
          <span className="material-symbols-outlined text-[28px]">
            {icon}
          </span>
        </div>

        <span
          className="
            font-data
            mt-6 block
            text-[10px]
            text-[#49607e]
          "
        >
          {number}
        </span>

        <h3
          className="
            font-title
            mt-1 text-xl
            font-bold
          "
        >
          {title}
        </h3>

        <p
          className="
            mt-3 leading-7
            text-[#3e4942]
          "
        >
          {description}
        </p>
      </div>

      <div
        className="
          font-data
          mt-6 flex
          items-center gap-1
          text-[10px]
          font-semibold
          text-[#006b47]
        "
      >
        {footer}

        <span className="material-symbols-outlined text-[16px]">
          check_circle
        </span>
      </div>
    </article>
  );
}