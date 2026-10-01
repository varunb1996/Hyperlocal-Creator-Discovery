import { contributions, points } from "@/lib/format";
import type { CreatorRow } from "@/lib/types";
import { cn } from "@/lib/utils";

const SEGMENTS = [
  { key: "locality", label: "Location", weight: 50, color: "bg-seg-locality" },
  { key: "content", label: "Content", weight: 30, color: "bg-seg-content" },
  { key: "engagement", label: "Engagement", weight: 20, color: "bg-seg-engagement" },
] as const;

/** One bar = the final score (full track = 100 points), split into each factor's weighted contribution. */
export function ScoreBar({ row, className }: { row: CreatorRow; className?: string }) {
  const parts = contributions(row);
  const label =
    `Score ${points(row.final_score)} out of 100: ` +
    SEGMENTS.map((s) => `${s.label.toLowerCase()} ${points(row[s.key])}`).join(", ");
  return (
    <div role="img" aria-label={label} className={cn("flex h-2 w-full overflow-hidden rounded-full bg-track", className)}>
      {SEGMENTS.map((s) => (
        <div
          key={s.key}
          className={cn(s.color, "h-full border-r border-card last:border-r-0 motion-safe:transition-[width] motion-safe:duration-500")}
          style={{ width: `${parts[s.key] * 100}%` }}
        />
      ))}
    </div>
  );
}

/** The three sub-scores as a compact legend that doubles as the bar's key. */
export function SubScores({ row }: { row: CreatorRow }) {
  return (
    <dl className="grid grid-cols-3 gap-2">
      {SEGMENTS.map((s) => (
        <div key={s.key} className="min-w-0">
          <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span aria-hidden className={cn("size-2 shrink-0 rounded-[2px]", s.color)} />
            {s.label}
            <span className="sr-only">(weight {s.weight}%)</span>
          </dt>
          <dd className="mt-0.5 text-sm font-medium tabular-nums">{points(row[s.key])}</dd>
        </div>
      ))}
    </dl>
  );
}
