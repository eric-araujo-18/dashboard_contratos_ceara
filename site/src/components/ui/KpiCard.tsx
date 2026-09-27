interface KpiCardProps {
  title: string;
  icon: string;
  value: string;
  description: string;
  color: string;
}

export default function KpiCard({
  title,
  icon,
  value,
  description,
  color,
}: KpiCardProps) {
  return (
    <article
      className="
        card-hover soft-shadow
        flex min-h-[155px]
        flex-col justify-between
        rounded-2xl
        bg-white p-5
      "
    >
      <div
        className="
          flex items-center
          justify-between
        "
      >
        <span
          className="
            text-sm
            text-[#49607e]
          "
        >
          {title}
        </span>

        <span
          style={{ color }}
          className="
            material-symbols-outlined
            text-[21px]
          "
        >
          {icon}
        </span>
      </div>

      <div className="mt-4">
        <div
          className="
            font-title
            text-3xl font-bold
          "
        >
          {value}
        </div>

        <div
          className="
            font-data
            mt-1 text-[10px]
            text-[#49607e]
          "
        >
          {description}
        </div>
      </div>
    </article>
  );
}