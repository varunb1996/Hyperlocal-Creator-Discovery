// Shapes returned by the FastAPI backend.

export type Vocab = {
  tone_preference: string[];
  budget_preference: string[];
  campaign_objective: string[];
  preferred_format: string[];
  price_bracket: string[];
};

export type CreatorRow = {
  rank: number;
  handle: string;
  final_score: number;
  locality: number;
  content: number;
  engagement: number;
  locality_tier: "Verified" | "Proxy" | "Unknown";
  confidence: string;
  engagement_confidence: "verified" | "unverified";
  engagement_capped: boolean;
  rate_band: string | null;
  rationale: string;
  explanation: string[];
};

export type SkippedCreator = {
  rank: number;
  handle: string;
  rate_band: string | null;
  reason: string;
};

export type ShortlistResponse = {
  brief_id: string | null; // null when re-ranked without saving
  shortlist_id: string | null;
  created_at: string | null;
  supported: boolean;
  message: string | null;
  scored_on: {
    city: string;
    tone_preference: string;
    weights: { locality: number; content: number; engagement: number };
  } | null;
  context_not_used_in_ranking: Record<string, string>;
  budget: {
    preference: string;
    max_budget_inr: number | null;
    filter_on: boolean;
    note: string | null;
    skipped_higher_ranked: SkippedCreator[];
  };
  eligible: number;
  rows: CreatorRow[];
};
