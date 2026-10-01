"use client";

import { ChevronDown } from "lucide-react";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { points, rateRange } from "@/lib/format";
import type { CreatorRow } from "@/lib/types";

import { ConfidenceBadges } from "./confidence";
import { ScoreBar, SubScores } from "./score-bar";

export function Explanation({ lines }: { lines: string[] }) {
  return (
    <ul className="space-y-2 text-sm leading-relaxed text-foreground/85">
      {lines.map((line) => (
        <li key={line} className="max-w-[68ch]">
          {line}
        </li>
      ))}
    </ul>
  );
}

/** Phone layout: one card per creator; "why this rank" expands in place. */
export function CreatorCard({ row }: { row: CreatorRow }) {
  const rate = rateRange(row.rate_band);
  return (
    <article className="rounded-xl border bg-card" aria-labelledby={`h-${row.rank}`}>
      <div className="p-4">
        <div className="flex items-start gap-3">
          <span className="w-8 shrink-0 text-2xl font-semibold leading-none tabular-nums text-muted-foreground/70">
            {row.rank}
          </span>
          <div className="min-w-0 flex-1">
            <h3 id={`h-${row.rank}`} className="truncate text-base font-semibold">
              {row.handle}
            </h3>
            {rate && (
              <p className="mt-0.5 text-sm text-muted-foreground">
                Est. rate <span className="tabular-nums text-foreground">{rate}</span>
              </p>
            )}
          </div>
          <div className="text-right">
            <p className="text-2xl font-semibold leading-none tabular-nums">{points(row.final_score)}</p>
            <p className="mt-1 text-xs text-muted-foreground">out of 100</p>
          </div>
        </div>

        <ScoreBar row={row} className="mt-4" />
        <div className="mt-3">
          <SubScores row={row} />
        </div>
        <ConfidenceBadges row={row} className="mt-3" />
      </div>

      <Collapsible>
        <CollapsibleTrigger className="group flex min-h-11 w-full items-center justify-between border-t px-4 text-sm font-medium text-primary outline-none focus-visible:bg-accent">
          Why this rank
          <ChevronDown aria-hidden className="size-4 transition-transform group-data-[panel-open]:rotate-180" />
        </CollapsibleTrigger>
        <CollapsibleContent className="px-4 pb-4">
          <Explanation lines={row.explanation} />
        </CollapsibleContent>
      </Collapsible>
    </article>
  );
}
