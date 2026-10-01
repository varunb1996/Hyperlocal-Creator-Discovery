import Link from "next/link";

/** Mark: a ranked shortlist in miniature (three bars, longest first). Same drawing as app/icon.svg. */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={className}>
      <rect width="32" height="32" rx="9" fill="var(--primary)" />
      <rect x="7" y="8.5" width="18" height="3.5" rx="1.75" fill="#fff" />
      <rect x="7" y="14.25" width="13" height="3.5" rx="1.75" fill="#fff" fillOpacity="0.8" />
      <rect x="7" y="20" width="8" height="3.5" rx="1.75" fill="#fff" fillOpacity="0.6" />
    </svg>
  );
}

export function Brand() {
  return (
    <Link href="/" className="flex min-w-0 items-center gap-2.5 rounded-lg outline-none focus-visible:ring-3 focus-visible:ring-ring/30">
      <BrandMark className="size-9 shrink-0" />
      <span className="truncate text-xl leading-none font-semibold tracking-tight">Creator Discovery</span>
      <span className="hidden shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary sm:inline">
        Pune pilot
      </span>
    </Link>
  );
}
