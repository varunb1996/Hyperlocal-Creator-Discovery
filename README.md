# Creator Discovery

A creator-to-café matching tool. A team member enters a café or restaurant's requirements and gets the **top 5 Pune Instagram creators**, ranked and explained, on a phone or a laptop.

The ranking is **fully deterministic**: plain Python arithmetic, no LLM, same input → same output. Every score comes with a plain-language "why this rank" and a confidence label, so the team can see at a glance what is measured and what is inferred.

![CI](https://github.com/varunb1996/Hyperlocal-Creator-Discovery/actions/workflows/ci.yml/badge.svg)

## Live

| | Link |
|---|---|
| **App** (new brief) | https://hyperlocal-creator-discovery.vercel.app |
| **Past shortlists** | https://hyperlocal-creator-discovery.vercel.app/history |
| **API docs** (interactive) | https://creator-discovery-api-6p1r.onrender.com/docs |
| **API health** | https://creator-discovery-api-6p1r.onrender.com/health |

The API runs on Render's free plan and sleeps when idle: the first request after a quiet spell can take 30–50 seconds. Open the app a minute before a demo.

## What it does

- **Ranks creators on three factors:** location fit (50%), content-tone match (30%) and engagement (20%).
- **Shows confidence, not just scores.** Green = measured or cross-checked, amber = inferred or not cross-checked. A creator whose Pune relevance is only inferred can never outrank one with a measured Pune audience.
- **Nudges down questionable audiences (v2).** A creator whose audience authenticity read is "Some Red Flags" or "Likely Inflated" has their engagement scaled by 0.85 or 0.7, shown with an amber badge.
- **Resolves near-ties clearly (v2).** Scores within 0.1 points are ordered by measured location first, then location fit, engagement and handle, with a note on the card.
- **Explains every rank** in five plain lines (overall, location, content, engagement, estimated rate).
- **Optional budget filter** (off by default) hides creators whose *estimated* rate is above the café's max spend. It only hides rows; it never re-orders or re-scores, and hidden higher ranks are listed with the reason.
- **Saves every shortlist** with its brief; a **History** page lists past shortlists and reopens any of them.
- **Pune pilot scope:** other cities are accepted but get a clear "not supported yet" message instead of a misleading list.

## Stack

| Layer | Tech |
|---|---|
| Data cleanup + scoring | Python 3.12 (`normalize.py`, `validate.py`, `scorer.py`, `shortlist.py`) |
| API | FastAPI (`api.py`) |
| Database | Supabase Postgres via its REST API (`db.py`, `schema.sql`) |
| Frontend | Next.js 16 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + TanStack Table (`web/`) |
| CI / deploy | GitHub Actions (`.github/workflows/ci.yml`), Render (`render.yaml`), Vercel |

Data flows **browser → Next.js server → FastAPI → Supabase**. The browser never talks to the API or the database directly, and the Supabase key only ever lives on the backend.

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for how it works and why, and **[DEPLOY.md](DEPLOY.md)** to put it online.

## Project structure

```
.
├── normalize.py      Phase 1: map free-text creator fields to the fixed vocabulary
├── validate.py       Phase 3: engagement-rate (ER) consistency checks
├── scorer.py         Phase 2: deterministic ranking + rationale/explanations
├── config.py         All scoring levers (weights, caps, score maps, tone matrix)
├── shortlist.py      Requirements input, budget filter, Pune scope guard, CLI
├── db.py             Supabase data access (no scoring)
├── seed.py           One-time: clean + validate creators, load into Supabase
├── api.py            FastAPI: /health, /vocab, /shortlist
├── schema.sql        Supabase tables (run once in the SQL editor)
├── data/
│   ├── mapping_tables.xlsx   Free-text → vocabulary mapping (the normalization spec)
│   ├── vocab.json            Fixed vocabulary, exported by seed.py (used by the API)
│   └── creator_workbook.xlsx Creator data — PRIVATE, not in this repo (see Data)
├── tests/            69 tests (pytest)
├── web/              Next.js frontend
├── render.yaml       Render blueprint for the API
└── .github/workflows/ci.yml
```

## Data

The creator workbook (`data/creator_workbook.xlsx`) holds real creators' names and Instagram handles, so it is **kept out of this public repo**. To run everything locally, place it at that path (or point `CREATORS_XLSX` at it). It needs two sheets:

- **Influencer Master**: one row per creator (handle, followers, engagements, ER%, top-5 audience cities with shares, content category/tone, base location, features-Pune, posting pace, estimated rate band…).
- **Cafe Profiles**: example cafés used as seed briefs.
- **Lists**: the fixed controlled vocabulary.

Email, phone and address columns are **never** loaded into the database: `seed.py` sends only a whitelist of columns (`db.CREATOR_FIELDS`).

## Run it locally

Prerequisites: Python 3.12+, Node.js 20.9+, a Supabase project.

### 1. Backend

```bash
python -m pip install -r requirements.txt
cp .env.example .env          # then fill in SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
```

In the Supabase **SQL Editor**, run [`schema.sql`](schema.sql) once. Then load the creators (needs the private workbook):

```bash
python seed.py
```

Start the API:

```bash
python -m uvicorn api:app --reload
```

Interactive API docs: http://127.0.0.1:8000/docs

### 2. Frontend

```bash
cd web
npm install
cp .env.example .env.local    # API_URL=http://127.0.0.1:8000
npm run dev
```

Open http://localhost:3000.

### 3. Tests

```bash
python -m pytest -v
```

With the workbook present, all 69 tests run (one also checks live Supabase when `SUPABASE_URL` is set). Without it — as on GitHub CI — data-dependent tests skip with a reason and the synthetic, validation-rule and API-boot tests still run.

## Configuration

| Variable | Where | Purpose |
|---|---|---|
| `SUPABASE_URL` | backend `.env` / Render | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | backend `.env` / Render | Server-side key. **Never** put it in the frontend. |
| `API_URL` | `web/.env.local` / Vercel | Where the Next.js server reaches FastAPI. Server-only. |
| `CREATORS_XLSX`, `MAPPINGS_XLSX`, `VOCAB_JSON` | optional | Override default data paths |

Scoring levers (weights, proxy cap, posting-pace map, tone-match matrix, ER rules, shortlist size) live in [`config.py`](config.py).

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Redirects to `/docs` (interactive API docs) |
| `GET` | `/health` | Liveness check |
| `GET` | `/vocab` | Dropdown values for the form (tone, budget, objective, format, price) |
| `POST` | `/shortlist` | Rank creators for a brief. Saves it unless `"save": false`. Returns top 5 (`top_n` to change) |
| `GET` | `/shortlists` | Past shortlists, newest first (café name, area, city, tone, date); `limit` up to 200 |
| `GET` | `/shortlist/{id}` | A saved shortlist, in the same shape as the POST response |

Example request:

```json
{
  "city": "Pune",
  "tone_preference": "Aesthetic/Calm",
  "budget_preference": "Paid Only",
  "max_budget_inr": 2500,
  "budget_filter": true,
  "name": "Example Cafe",
  "area": "Baner"
}
```

## Known limitations

- **Pune only.** The creator pool is Pune-based; other cities return a not-supported message.
- **Rates are estimates.** No public rate cards exist; the budget filter is labelled as such and is off by default.
- **No barter data.** Every creator has a paid estimate, so "Barter Only" is recorded on the brief but does not filter.
- **Location is partly inferred.** About 60% of creators have no audience-city data; their location fit is inferred from base location and venue features and capped below every measured creator.
