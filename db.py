"""Supabase data access. Thin: storage <-> the dict shape scorer.rank() already expects. No scoring here."""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

AUDIENCE_SLOTS = [(f"City {i}", f"City {i} %") for i in range(1, 6)]

# creators column -> scorer key. Whitelist: nothing outside this (e.g. email/phone/address) is ever stored.
CREATOR_FIELDS = {
    "handle": "Username",
    "creator_name": "Creator",
    "content_category": "content_category",
    "content_tone": "content_tone",
    "features_pune": "features_pune",
    "base_location": "Creator Base Location (City/Area)",
    "er": "ER%",
    "posting_pace": "Posting Pace Category",
    "engagement_confidence": "engagement_confidence",
    "er_implausible": "er_implausible",
    "authenticity": "authenticity",
    "rate_band": "Rate Band",
}


class Supabase:
    """Minimal PostgREST client (Supabase REST API)."""

    def __init__(self, url, key, transport=None):
        base = url.strip().rstrip("/").removesuffix("/rest/v1")  # accept project URL or REST endpoint
        self.http = httpx.Client(
            base_url=base + "/rest/v1", transport=transport, timeout=30,
            headers={"apikey": key, "Authorization": f"Bearer {key}"})

    def select(self, table, **params):
        r = self.http.get(f"/{table}", params={"select": "*", **params})
        r.raise_for_status()
        return r.json()

    def insert(self, table, rows, upsert_on=None):
        prefer = "return=representation" + (",resolution=merge-duplicates" if upsert_on else "")
        params = {"on_conflict": upsert_on} if upsert_on else None
        r = self.http.post(f"/{table}", json=rows, params=params, headers={"Prefer": prefer})
        r.raise_for_status()
        return r.json()


def from_env():
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set (see .env.example)")
    return Supabase(url, key)


def to_db_row(creator):
    """Validated scorer-shaped creator -> creators row."""
    row = {col: creator.get(key) for col, key in CREATOR_FIELDS.items()}
    row["er_implausible"] = bool(row["er_implausible"])
    row["audience_cities"] = [[creator[c], creator.get(p)] for c, p in AUDIENCE_SLOTS if creator.get(c)]
    return row


def from_db_row(row):
    """creators row -> the dict shape scorer.rank() expects."""
    creator = {key: row.get(col) for col, key in CREATOR_FIELDS.items()}
    for (c, p), (city, share) in zip(AUDIENCE_SLOTS, row.get("audience_cities") or []):
        creator[c], creator[p] = city, share
    return creator


def load_creators(db):
    return [from_db_row(r) for r in db.select("creators", order="handle.asc")]


CONTEXT_COLUMNS = ("area", "campaign_objective", "preferred_format", "price_bracket", "vibe")


def records(req, budget_filter_on, result, skipped):
    """(cafe_briefs row, shortlists row) for a generated shortlist, before saving."""
    ctx = req["context"]
    brief = {"city": req["city"], "tone_preference": req["tone_pref"], "budget_preference": req["budget_preference"],
             "max_budget_inr": req["max_budget_inr"], "budget_filter_on": budget_filter_on, "name": ctx.get("name"),
             **{k: ctx.get(k) for k in CONTEXT_COLUMNS}}
    shortlist = {"scope_message": result["message"], "eligible": result["eligible"],
                 "filter_note": result["filter_note"], "skipped": skipped, "rows": result["rows"]}
    return brief, shortlist


def save_shortlist(db, brief, shortlist):
    """Persist the brief and its shortlist. Returns the stored rows (with ids and timestamps)."""
    saved_brief = db.insert("cafe_briefs", [brief])[0]
    saved_shortlist = db.insert("shortlists", [{**shortlist, "brief_id": saved_brief["id"]}])[0]
    return saved_brief, saved_shortlist


def list_shortlists(db, limit=50):
    """Newest shortlists with their brief's headline fields (no ranked rows, so it stays light)."""
    shortlists = db.select("shortlists", select="id,brief_id,created_at,scope_message",
                           order="created_at.desc", limit=str(limit))
    if not shortlists:
        return []
    ids = ",".join(s["brief_id"] for s in shortlists)
    briefs = {b["id"]: b for b in db.select("cafe_briefs", id=f"in.({ids})")}
    out = []
    for s in shortlists:
        b = briefs.get(s["brief_id"], {})
        out.append({"shortlist_id": s["id"], "created_at": s["created_at"], "supported": s["scope_message"] is None,
                    "name": b.get("name"), "area": b.get("area"), "city": b.get("city"),
                    "tone_preference": b.get("tone_preference"), "budget_preference": b.get("budget_preference")})
    return out


def get_shortlist(db, shortlist_id):
    """(brief row, shortlist row) or None."""
    found = db.select("shortlists", id=f"eq.{shortlist_id}")
    if not found:
        return None
    return db.select("cafe_briefs", id=f"eq.{found[0]['brief_id']}")[0], found[0]
