"use client";

import { ChevronDown } from "lucide-react";
import { useActionState, useState } from "react";

import { submitBrief, type FormState } from "@/app/actions";
import { Button } from "@/components/ui/button";
import type { Vocab } from "@/lib/types";

// 16px text on inputs stops iOS Safari zooming in on focus.
const control =
  "h-11 w-full rounded-lg border border-input bg-card px-3 text-[16px] outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20 disabled:bg-muted disabled:text-muted-foreground";

function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      {hint && (
        <p id={`${id}-hint`} className="mt-0.5 text-xs text-muted-foreground">
          {hint}
        </p>
      )}
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

function Select({
  id,
  options,
  placeholder,
  defaultValue,
  required,
  onChange,
}: {
  id: string;
  options: string[];
  placeholder?: string;
  defaultValue?: string;
  required?: boolean;
  onChange?: (v: string) => void;
}) {
  return (
    <div className="relative">
      <select
        id={id}
        name={id}
        required={required}
        defaultValue={defaultValue ?? ""}
        onChange={(e) => onChange?.(e.target.value)}
        className={`${control} appearance-none pr-9`}
      >
        {placeholder && (
          <option value="" disabled={required}>
            {placeholder}
          </option>
        )}
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
      <ChevronDown aria-hidden className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  );
}

function Section({ title, note, children }: { title: string; note: string; children: React.ReactNode }) {
  return (
    <fieldset className="rounded-xl border bg-card p-4 sm:p-5">
      <legend className="sr-only">{title}</legend>
      <h2 aria-hidden className="text-base font-semibold">
        {title}
      </h2>
      <p className="mt-0.5 text-sm text-muted-foreground">{note}</p>
      <div className="mt-4 space-y-4">{children}</div>
    </fieldset>
  );
}

export function BriefForm({ vocab }: { vocab: Vocab }) {
  const [state, action, pending] = useActionState<FormState, FormData>(submitBrief, { error: null });
  const [budget, setBudget] = useState("Not Yet Decided");
  const paid = budget === "Paid Only";

  return (
    <form action={action} className="space-y-4" noValidate={false}>
      <Section title="What we rank on" note="These two decide the ranking.">
        <Field id="city" label="City" hint="The creator pool covers Pune.">
          <input id="city" name="city" defaultValue="Pune" required autoComplete="address-level2" aria-describedby="city-hint" className={control} />
        </Field>
        <Field id="tone_preference" label="Content tone">
          <Select id="tone_preference" options={vocab.tone_preference} placeholder="Choose a tone" required />
        </Field>
      </Section>

      <Section title="Budget" note="Used only to hide creators whose estimated rates are over budget.">
        <Field id="budget_preference" label="Budget type">
          <Select id="budget_preference" options={vocab.budget_preference} defaultValue="Not Yet Decided" onChange={setBudget} />
        </Field>
        <Field id="max_budget_inr" label="Max spend per creator (₹)" hint={paid ? undefined : "Available for paid budgets."}>
          <input
            id="max_budget_inr"
            name="max_budget_inr"
            type="number"
            inputMode="numeric"
            min={1}
            step={1}
            placeholder="e.g. 3000"
            disabled={!paid}
            aria-describedby={paid ? undefined : "max_budget_inr-hint"}
            className={`${control} tabular-nums`}
          />
        </Field>
      </Section>

      <Section title="About the café" note="For your records and the shortlist header. Not used in ranking.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="name" label="Café name">
            <input id="name" name="name" autoComplete="organization" className={control} />
          </Field>
          <Field id="area" label="Area">
            <input id="area" name="area" placeholder="e.g. Baner" className={control} />
          </Field>
          <Field id="campaign_objective" label="Campaign goal">
            <Select id="campaign_objective" options={vocab.campaign_objective} placeholder="Not set" />
          </Field>
          <Field id="preferred_format" label="Preferred format">
            <Select id="preferred_format" options={vocab.preferred_format} placeholder="Not set" />
          </Field>
          <Field id="price_bracket" label="Price for two">
            <Select id="price_bracket" options={vocab.price_bracket} placeholder="Not set" />
          </Field>
        </div>
        <Field id="vibe" label="Vibe">
          <textarea id="vibe" name="vibe" rows={2} placeholder="e.g. Calm garden café with coworking tables" className={`${control} h-auto py-2.5`} />
        </Field>
      </Section>

      {state.error && (
        <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {state.error}
        </p>
      )}

      <Button type="submit" disabled={pending} className="h-12 w-full rounded-xl text-base font-medium sm:w-auto sm:px-8">
        {pending ? "Finding creators…" : "Find creators"}
      </Button>
    </form>
  );
}
