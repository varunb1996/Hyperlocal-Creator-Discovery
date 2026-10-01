"use client";

import { createColumnHelper, tableFeatures, useTable } from "@tanstack/react-table";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { points, rateRange } from "@/lib/format";
import type { CreatorRow } from "@/lib/types";
import { cn } from "@/lib/utils";

import { ConfidenceBadges } from "./confidence";
import { ScoreBar } from "./score-bar";

const features = tableFeatures({});
const col = createColumnHelper<typeof features, CreatorRow>();

const columns = col.columns([
  col.accessor("rank", {
    header: "Rank",
    cell: ({ getValue }) => <span className="tabular-nums text-muted-foreground">{getValue()}</span>,
  }),
  col.accessor("handle", {
    header: "Creator",
    cell: ({ getValue }) => <span className="font-medium">{getValue()}</span>,
  }),
  col.display({
    id: "score",
    header: "Score out of 100",
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <span className="w-8 font-semibold tabular-nums">{points(row.original.final_score)}</span>
        <ScoreBar row={row.original} className="w-36" />
      </div>
    ),
  }),
  col.display({
    id: "confidence",
    header: "Confidence",
    cell: ({ row }) => <ConfidenceBadges row={row.original} className="flex-col items-start" />,
  }),
  col.accessor("rate_band", {
    header: "Est. rate",
    cell: ({ getValue }) => <span className="tabular-nums">{rateRange(getValue()) ?? "–"}</span>,
  }),
]);

/** Desktop layout. Selecting a row shows its "why this rank" in the side panel. */
export function ResultsTable({
  rows,
  selectedRank,
  onSelect,
}: {
  rows: CreatorRow[];
  selectedRank: number | null;
  onSelect: (rank: number) => void;
}) {
  const table = useTable({ features, columns, data: rows });
  return (
    <div className="rounded-xl border bg-card">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((hg) => (
            <TableRow key={hg.id} className="hover:bg-transparent">
              {hg.headers.map((h) => (
                <TableHead key={h.id} className="h-11 px-4 text-xs font-medium text-muted-foreground">
                  <table.FlexRender header={h} />
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((r) => {
            const rank = r.original.rank;
            const selected = rank === selectedRank;
            return (
              <TableRow
                key={r.id}
                aria-selected={selected}
                tabIndex={0}
                onClick={() => onSelect(rank)}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onSelect(rank))}
                className={cn(
                  "cursor-pointer outline-none focus-visible:bg-accent",
                  selected && "bg-primary/[0.06] hover:bg-primary/[0.08]",
                )}
              >
                {r.getAllCells().map((c) => (
                  <TableCell key={c.id} className="px-4 py-3 align-middle">
                    <table.FlexRender cell={c} />
                  </TableCell>
                ))}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
