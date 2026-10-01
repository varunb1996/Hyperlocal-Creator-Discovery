"use client";

import { useState, useTransition } from "react";

import { rerank } from "@/app/actions";
import type { ShortlistResponse } from "@/lib/types";

import { ResultsView } from "./results-view";

/** Holds the shown shortlist; the budget toggle re-asks the backend (re-rank only, nothing saved). */
export function ShortlistClient({ initial }: { initial: ShortlistResponse }) {
  const [data, setData] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const onBudgetFilterChange = (on: boolean) =>
    startTransition(async () => {
      try {
        setData(await rerank(data, on));
        setError(null);
      } catch {
        setError("Couldn't update the list. Check your connection and try again.");
      }
    });

  return <ResultsView data={data} pending={pending} error={error} onBudgetFilterChange={onBudgetFilterChange} />;
}
