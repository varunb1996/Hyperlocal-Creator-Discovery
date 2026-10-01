import { ChevronDown } from "lucide-react";

import type { ShortlistResponse } from "@/lib/types";

const CONTEXT_LABELS: Record<string, string> = {
  area: "Area",
  campaign_objective: "Campaign goal",
  preferred_format: "Format",
  price_bracket: "Price for two",
  vibe: "Vibe",
};

const CONTEXT_TITLE = "Brief context, not used in ranking";

function ContextList({ entries, ctx }: { entries: [string, string][]; ctx: Record<string, string> }) {
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3 xl:grid-cols-5">
      {entries.map(([k, label]) => (
        <div key={k} className={k === "vibe" ? "col-span-2 sm:col-span-3 xl:col-span-1" : undefined}>
          <dt className="text-xs text-muted-foreground">{label}</dt>
          <dd className="mt-0.5 text-sm">{ctx[k]}</dd>
        </div>
      ))}
    </dl>
  );
}

/** The café's brief. Separates what drives the ranking from context that does not. */
export function BriefSummary({ data }: { data: ShortlistResponse }) {
  const ctx = data.context_not_used_in_ranking;
  const entries = Object.entries(CONTEXT_LABELS).filter(([k]) => ctx[k]);
  return (
    <header>
      <h1 className="text-2xl font-semibold tracking-tight">{ctx.name ?? "Shortlist"}</h1>
      {data.scored_on && (
        <p className="mt-1 text-base text-muted-foreground">
          Ranked for <span className="font-medium text-foreground">{data.scored_on.city}</span> on location fit,{" "}
          <span className="font-medium text-foreground">{data.scored_on.tone_preference}</span> tone and engagement,
          from <span className="tabular-nums">{data.eligible}</span> eligible creators
        </p>
      )}
      {entries.length > 0 && (
        <>
          {/* Phone: collapsed so the creators come first */}
          <details className="group mt-4 rounded-xl border border-dashed xl:hidden">
            <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between px-4 text-sm text-muted-foreground [&::-webkit-details-marker]:hidden">
              {CONTEXT_TITLE}
              <ChevronDown aria-hidden className="size-4 transition-transform group-open:rotate-180" />
            </summary>
            <div className="px-4 pb-4">
              <ContextList entries={entries} ctx={ctx} />
            </div>
          </details>
          {/* Desktop: always visible */}
          <section aria-label={CONTEXT_TITLE} className="mt-4 hidden rounded-xl border border-dashed p-4 xl:block">
            <p className="text-sm text-muted-foreground">{CONTEXT_TITLE}</p>
            <div className="mt-3">
              <ContextList entries={entries} ctx={ctx} />
            </div>
          </section>
        </>
      )}
    </header>
  );
}
