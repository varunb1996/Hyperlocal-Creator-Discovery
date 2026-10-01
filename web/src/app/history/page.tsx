import { ChevronRight } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { ApiError, getHistory } from "@/lib/api";
import type { HistoryItem } from "@/lib/types";

// Servers (e.g. Vercel) run in UTC; the team works in India time.
const IST = "Asia/Kolkata";
const yearOf = (d: Date) => new Intl.DateTimeFormat("en-IN", { timeZone: IST, year: "numeric" }).format(d);

/** "1 Oct, 7:38 pm"; the year is added only for past years. */
function when(iso: string) {
  const d = new Date(iso);
  const withYear = yearOf(d) !== yearOf(new Date());
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: IST,
    day: "numeric",
    month: "short",
    ...(withYear && { year: "numeric" }),
    hour: "numeric",
    minute: "2-digit",
  }).format(d);
}

function Row({ item }: { item: HistoryItem }) {
  const place = [item.area, item.city].filter(Boolean).join(", ");
  return (
    <Link
      href={`/shortlist/${item.shortlist_id}`}
      className="flex min-h-16 items-center gap-3 px-4 py-3 outline-none hover:bg-accent/60 focus-visible:bg-accent"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <p className={item.name ? "truncate font-medium" : "truncate font-medium text-muted-foreground"}>
            {item.name ?? "Unnamed brief"}
          </p>
          <time dateTime={item.created_at} className="shrink-0 text-xs tabular-nums text-muted-foreground">
            {when(item.created_at)}
          </time>
        </div>
        <p className="mt-1 flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
          <span className="truncate">{place}</span>
          <span className="shrink-0 rounded-md bg-muted px-1.5 py-0.5 text-xs text-foreground/80">
            {item.supported ? item.tone_preference : "City not supported"}
          </span>
        </p>
      </div>
      <ChevronRight aria-hidden className="size-4 shrink-0 text-muted-foreground" />
    </Link>
  );
}

export default async function HistoryPage() {
  let items: HistoryItem[] = [];
  let error: string | null = null;
  try {
    items = await getHistory();
  } catch (e) {
    error = e instanceof ApiError ? e.message : "Couldn't load past shortlists.";
  }

  return (
    <main className="mx-auto w-full max-w-2xl px-4 pt-6 pb-16">
      <h1 className="text-2xl font-semibold tracking-tight">Past shortlists</h1>
      <p className="mt-1 text-base text-muted-foreground">Every saved brief, newest first. Tap one to reopen its ranking.</p>

      <div className="mt-6">
        {error ? (
          <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {error}
          </p>
        ) : items.length === 0 ? (
          <div className="rounded-xl border bg-card p-5">
            <p className="text-base font-medium">No shortlists yet</p>
            <p className="mt-1 text-sm text-muted-foreground">Create one for a café and it will appear here.</p>
            <Link href="/" className={buttonVariants({ className: "mt-4 h-11 rounded-xl px-5" })}>
              New brief
            </Link>
          </div>
        ) : (
          <ul className="divide-y overflow-hidden rounded-xl border bg-card">
            {items.map((item) => (
              <li key={item.shortlist_id}>
                <Row item={item} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
