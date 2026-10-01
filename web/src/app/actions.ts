"use server";

import { redirect } from "next/navigation";

import { ApiError, postShortlist } from "@/lib/api";
import type { ShortlistResponse } from "@/lib/types";

export type FormState = { error: string | null };

const TEXT_FIELDS = ["city", "tone_preference", "budget_preference", "name", "area", "campaign_objective",
  "preferred_format", "price_bracket", "vibe"] as const;

/** Submit a café brief: ranks, saves, and opens the shortlist's own page. */
export async function submitBrief(_prev: FormState, form: FormData): Promise<FormState> {
  const brief: Record<string, unknown> = {};
  for (const f of TEXT_FIELDS) {
    const v = String(form.get(f) ?? "").trim();
    if (v) brief[f] = v;
  }
  const max = String(form.get("max_budget_inr") ?? "").trim();
  if (brief.budget_preference === "Paid Only" && max) {
    const n = Number(max);
    if (!Number.isInteger(n) || n <= 0) return { error: "Max spend per creator must be a whole number of rupees." };
    brief.max_budget_inr = n;
  }

  let id: string | null;
  try {
    id = (await postShortlist(brief)).shortlist_id;
  } catch (e) {
    return { error: e instanceof ApiError ? e.message : "Something went wrong. Try again." };
  }
  redirect(`/shortlist/${id}`);
}

/** Re-rank the same brief with the budget filter on or off, without saving a new shortlist. */
export async function rerank(data: ShortlistResponse, budgetFilter: boolean): Promise<ShortlistResponse> {
  if (!data.scored_on) return data;
  return postShortlist({
    ...data.context_not_used_in_ranking,
    city: data.scored_on.city,
    tone_preference: data.scored_on.tone_preference,
    budget_preference: data.budget.preference,
    max_budget_inr: data.budget.max_budget_inr,
    budget_filter: budgetFilter,
    top_n: data.rows.length || undefined,
    save: false,
  });
}
