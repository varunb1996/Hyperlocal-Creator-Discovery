import { CircleCheck, CircleDashed } from "lucide-react";

import type { CreatorRow } from "@/lib/types";
import { cn } from "@/lib/utils";

function ConfidenceBadge({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  const Icon = ok ? CircleCheck : CircleDashed;
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center gap-1 rounded-full px-2 text-xs font-medium whitespace-nowrap",
        ok ? "bg-verified-bg text-verified" : "bg-inferred-bg text-inferred",
      )}
    >
      <Icon aria-hidden className="size-3.5" />
      {children}
    </span>
  );
}

/** Location tier + engagement confidence. Green = measured/cross-checked, amber = inferred/unchecked. */
export function ConfidenceBadges({ row, className }: { row: CreatorRow; className?: string }) {
  const locationOk = row.locality_tier === "Verified";
  const locationText = locationOk ? "Location verified" : row.locality_tier === "Proxy" ? "Location inferred" : "Location unknown";
  const engagementOk = row.engagement_confidence === "verified";
  return (
    <div className={cn("flex flex-wrap gap-1.5", className)}>
      <ConfidenceBadge ok={locationOk}>{locationText}</ConfidenceBadge>
      <ConfidenceBadge ok={engagementOk}>{engagementOk ? "Engagement verified" : "Engagement unverified"}</ConfidenceBadge>
      {(row.authenticity_factor ?? 1) < 1 && (
        <ConfidenceBadge ok={false}>Authenticity: {row.authenticity?.toLowerCase()}</ConfidenceBadge>
      )}
    </div>
  );
}
