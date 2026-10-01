import type { CreatorRow } from "./types";

/** Scores are 0–1 in the API; shown as points out of 100. */
export const points = (n: number) => Math.round(n * 100);

/** "₹2,500–₹5,000 indicative; public rate card not found" -> "₹2,500–₹5,000" */
export const rateRange = (band: string | null) => (band ? band.split(" indicative")[0] : null);

/** Low end of an estimated range: "₹3,500–₹7,000 indicative…" -> "₹3,500" */
export const rateFrom = (band: string | null) => band?.match(/₹[\d,]+/)?.[0] ?? null;

export const inr = (n: number) => `₹${n.toLocaleString("en-IN")}`;

/** "Why this rank" lines; older saved shortlists only have the one-line rationale. */
export const explanationOf = (row: CreatorRow) => row.explanation ?? [row.rationale];

/** Weighted contribution of each factor to the final score (they sum to final_score). */
export function contributions(row: CreatorRow, weights = { locality: 50, content: 30, engagement: 20 }) {
  return {
    locality: (row.locality * weights.locality) / 100,
    content: (row.content * weights.content) / 100,
    engagement: (row.engagement * weights.engagement) / 100,
  };
}
