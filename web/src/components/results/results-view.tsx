"use client";

import { useState } from "react";

import { Switch } from "@/components/ui/switch";
import { explanationOf, inr, points, rateFrom, rateRange } from "@/lib/format";
import type { ShortlistResponse } from "@/lib/types";

import { BriefSummary } from "./brief-summary";
import { ConfidenceBadges } from "./confidence";
import { CreatorCard, Explanation } from "./creator-card";
import { ResultsTable } from "./results-table";
import { ScoreBar, SubScores } from "./score-bar";

function BudgetToggle({
  data,
  pending,
  onChange,
}: {
  data: ShortlistResponse;
  pending: boolean;
  onChange: (on: boolean) => void;
}) {
  const { preference, max_budget_inr, filter_on } = data.budget;
  const usable = preference === "Paid Only" && max_budget_inr !== null;
  const detail = usable
    ? `Hides creators whose lowest estimated rate is above ${inr(max_budget_inr!)}. Rates are estimates, not quotes.`
    : preference === "Barter Only"
      ? "No barter data on creators yet, so the list can't be filtered for barter. Rates shown are paid estimates."
      : "Set a paid budget with a max spend per creator to use this.";
  return (
    <label className="flex min-h-14 cursor-pointer items-center justify-between gap-4 rounded-xl border bg-card px-4 py-3 has-[[data-disabled]]:cursor-not-allowed">
      <span className="min-w-0">
        <span className="block text-sm font-medium">Hide over-budget creators</span>
        <span className="mt-0.5 block text-xs text-muted-foreground">{detail}</span>
      </span>
      <Switch checked={filter_on} disabled={!usable || pending} onCheckedChange={(on) => onChange(on)} />
    </label>
  );
}

/** One line naming the higher-ranked creators the budget filter hid, so gaps in the ranks are explained. */
function SkippedSummary({ data }: { data: ShortlistResponse }) {
  const skipped = data.budget.skipped_higher_ranked;
  if (skipped.length === 0) return null;
  const list = skipped.map((s) => {
    const from = rateFrom(s.rate_band);
    return `#${s.rank} ${s.handle}${from ? ` (est. from ${from})` : ""}`;
  });
  return (
    <p className="mt-4 rounded-xl border border-dashed px-4 py-3 text-sm text-muted-foreground">
      Hidden by budget: <span className="text-foreground">{list.join(", ")}</span>. Shown creators keep their original
      rank.
    </p>
  );
}

export function ResultsView({
  data,
  pending = false,
  error = null,
  onBudgetFilterChange,
}: {
  data: ShortlistResponse;
  pending?: boolean;
  error?: string | null;
  onBudgetFilterChange: (on: boolean) => void;
}) {
  const [selectedRank, setSelectedRank] = useState<number | null>(data.rows[0]?.rank ?? null);
  const selected = data.rows.find((r) => r.rank === selectedRank) ?? data.rows[0];
  const listKey = data.rows.map((r) => r.rank).join("-");

  return (
    <main className="mx-auto w-full max-w-2xl px-4 pt-6 pb-16 xl:max-w-7xl xl:px-8">
      <BriefSummary data={data} />

      <section aria-labelledby="shortlist-heading" className="mt-8">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 id="shortlist-heading" className="text-lg font-semibold">
              Top {data.rows.length} creators
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              <span className="font-medium text-verified">Green</span> means measured or cross-checked.{" "}
              <span className="font-medium text-inferred">Amber</span> means inferred or not cross-checked.
            </p>
          </div>
          <div className="xl:w-[26rem]">
            <BudgetToggle data={data} pending={pending} onChange={onBudgetFilterChange} />
          </div>
        </div>

        {error && (
          <p role="alert" className="mt-4 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {error}
          </p>
        )}
        <SkippedSummary data={data} />

        <div aria-live="polite" aria-busy={pending} className={pending ? "mt-4 opacity-60 transition-opacity" : "mt-4"}>
          {data.rows.length === 0 && (
            <p className="rounded-xl border bg-card px-4 py-6 text-sm text-muted-foreground">
              No creators fit this budget. Turn off the budget filter or raise the max spend per creator.
            </p>
          )}

          {/* Phone and tablet: cards */}
          <ol key={listKey} className="space-y-3 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300 xl:hidden">
            {data.rows.map((row) => (
              <li key={row.rank}>
                <CreatorCard row={row} />
              </li>
            ))}
          </ol>

          {/* Desktop: table + "why this rank" panel */}
          {selected && (
            <div key={`d-${listKey}`} className="hidden gap-6 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300 xl:grid xl:grid-cols-[minmax(0,1fr)_22rem]">
              <ResultsTable rows={data.rows} selectedRank={selected.rank} onSelect={setSelectedRank} />
              <aside aria-label={`Why ${selected.handle} ranks #${selected.rank}`} className="self-start rounded-xl border bg-card p-5 xl:sticky xl:top-6">
                <p className="text-sm text-muted-foreground">Why this rank</p>
                <div className="mt-1 flex items-baseline justify-between gap-3">
                  <h3 className="truncate text-lg font-semibold">
                    #{selected.rank} {selected.handle}
                  </h3>
                  <span className="text-xl font-semibold tabular-nums">
                    {points(selected.final_score)}
                    <span className="text-sm font-normal text-muted-foreground">/100</span>
                  </span>
                </div>
                <ScoreBar row={selected} className="mt-4" />
                <div className="mt-3">
                  <SubScores row={selected} />
                </div>
                <ConfidenceBadges row={selected} className="mt-4" />
                {rateRange(selected.rate_band) && (
                  <p className="mt-4 text-sm text-muted-foreground">
                    Est. rate <span className="tabular-nums text-foreground">{rateRange(selected.rate_band)}</span>
                  </p>
                )}
                <div className="mt-4 border-t pt-4">
                  <Explanation lines={explanationOf(selected)} />
                </div>
              </aside>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
