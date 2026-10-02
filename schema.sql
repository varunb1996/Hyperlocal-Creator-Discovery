-- Run once in the Supabase SQL editor. Supabase is the data store only; all scoring happens in Python.

create table if not exists creators (
  handle                text primary key,
  creator_name          text,
  content_category      text not null,              -- normalized (Phase 1)
  content_tone          text not null,              -- normalized (Phase 1)
  features_pune         text not null,              -- Yes | Occasionally | No
  base_location         text,
  audience_cities       jsonb not null default '[]', -- [[city, share], ...] top-5 audience cities
  er                    double precision,           -- validated ER (Phase 3)
  posting_pace          text,
  engagement_confidence text not null check (engagement_confidence in ('verified', 'unverified')),
  er_implausible        boolean not null default false,
  authenticity          text,                       -- enrichment's audience authenticity read (dampens engagement)
  rate_band             text,                       -- ESTIMATED rate range, display/filter only
  updated_at            timestamptz not null default now()
);

create table if not exists cafe_briefs (
  id                 uuid primary key default gen_random_uuid(),
  created_at         timestamptz not null default now(),
  city               text not null,
  tone_preference    text not null,
  budget_preference  text not null,
  max_budget_inr     integer,
  budget_filter_on   boolean not null default false,
  name               text,
  area               text,
  campaign_objective text,
  preferred_format   text,
  price_bracket      text,
  vibe               text
);

create table if not exists shortlists (
  id            uuid primary key default gen_random_uuid(),
  brief_id      uuid not null references cafe_briefs(id) on delete cascade,
  created_at    timestamptz not null default now(),
  scope_message text,             -- set when the city is outside the pilot (rows is then empty)
  eligible      integer not null,
  filter_note   text,
  skipped       jsonb not null default '[]', -- higher-ranked creators hidden by the budget filter, with reasons
  rows          jsonb not null    -- ranked shortlist exactly as returned by the API
);
-- Existing projects (created before `skipped` was added):
alter table shortlists add column if not exists skipped jsonb not null default '[]';
-- Existing projects (created before `authenticity` was added):
alter table creators add column if not exists authenticity text;

-- No policies: the anon key can read/write nothing. The backend uses the service-role key, which bypasses RLS.
alter table creators    enable row level security;
alter table cafe_briefs enable row level security;
alter table shortlists  enable row level security;
