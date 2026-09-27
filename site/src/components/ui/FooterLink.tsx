interface FooterLinkProps {
  icon: string;
  text: string;
  href: string;
}

export default function FooterLink({
  icon,
  text,
  href,
}: FooterLinkProps) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="
        flex items-center
        gap-2
        text-sm
        text-[#3e4942]
        transition
        hover:text-[#006b47]
      "
    >
      <span className="material-symbols-outlined text-[18px]">
        {icon}
      </span>

      {text}
    </a>
  );
}