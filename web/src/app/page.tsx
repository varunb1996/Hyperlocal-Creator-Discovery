import { BriefForm } from "@/components/brief-form";
import { ApiError, getVocab } from "@/lib/api";
import type { Vocab } from "@/lib/types";

export default async function Page() {
  let vocab: Vocab | null = null;
  let error: string | null = null;
  try {
    vocab = await getVocab();
  } catch (e) {
    error = e instanceof ApiError ? e.message : "Couldn't load the form.";
  }

  return (
    <main className="mx-auto w-full max-w-2xl px-4 pt-6 pb-16">
      <h1 className="text-2xl font-semibold tracking-tight">New creator shortlist</h1>
      <p className="mt-1 text-base text-muted-foreground">
        Tell us about the café or restaurant. We&apos;ll rank Pune creators on location fit, content tone and
        engagement, and show the top 5.
      </p>
      <div className="mt-6">
        {vocab ? (
          <BriefForm vocab={vocab} />
        ) : (
          <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {error}
          </p>
        )}
      </div>
    </main>
  );
}
