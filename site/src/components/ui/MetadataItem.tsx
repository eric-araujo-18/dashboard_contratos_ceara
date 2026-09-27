interface MetadataItemProps {
  label: string;
  value: string;
}

export default function MetadataItem({
  label,
  value,
}: MetadataItemProps) {
  return (
    <div>
      <div
        className="
          font-data
          text-[10px]
          text-[#49607e]
        "
      >
        {label}
      </div>

      <div
        className="
          mt-1
          text-sm font-semibold
        "
      >
        {value}
      </div>
    </div>
  );
}