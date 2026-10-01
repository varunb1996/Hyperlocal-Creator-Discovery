import Link from "next/link";
import { notFound } from "next/navigation";

import { ShortlistClient } from "@/components/results/shortlist-client";
import { buttonVariants } from "@/components/ui/button";
import { ApiError, getShortlist } from "@/lib/api";
import type { ShortlistResponse } from "@/lib/types";

export default async function ShortlistPage({ params }: PageProps<"/shortlist/[id]">) {
  const { id } = await params;
  let data: ShortlistResponse;
  try {
    data = await getShortlist(id);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 422)) notFound();
    throw e;
  }

  if (!data.supported) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 pt-6 pb-16">
        <h1 className="text-2xl font-semibold tracking-tight">{data.context_not_used_in_ranking.name ?? "Shortlist"}</h1>
        <div className="mt-6 rounded-xl border bg-card p-5">
          <p className="text-base font-medium">{data.message}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            The creator pool only covers Pune for now, so no ranking was made for this city.
          </p>
          <Link href="/" className={buttonVariants({ className: "mt-4 h-11 rounded-xl px-5" })}>
            Start a Pune brief
          </Link>
        </div>
      </main>
    );
  }

  return <ShortlistClient initial={data} />;
}
