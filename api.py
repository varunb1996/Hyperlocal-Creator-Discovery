"""FastAPI backend. Supabase is the data source; ranking is the unchanged Python scorer.

Run: uvicorn api:app --host 0.0.0.0 --port $PORT
"""
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

import config as cfg
import db
from shortlist import make_requirements, shortlist, skipped_above, skipped_note

VOCAB_JSON = os.getenv("VOCAB_JSON", str(Path(__file__).parent / "data" / "vocab.json"))

# Brief field -> Lists vocabulary key, for the form's dropdowns.
VOCAB_FIELDS = {"tone_preference": "ContentTonePref", "budget_preference": "BudgetPreference",
                "campaign_objective": "CampaignObjective", "preferred_format": "PreferredFormat",
                "price_bracket": "PriceBracket"}

app = FastAPI(title="Hyperlocal Creator Discovery")


class Brief(BaseModel):
    city: str = cfg.DEFAULT_CAFE_CITY
    tone_preference: Optional[str] = None
    budget_preference: Optional[str] = None
    max_budget_inr: Optional[int] = None
    budget_filter: bool = False  # hide creators over budget (ESTIMATED rates); off by default
    top_n: int = Field(cfg.SHORTLIST_SIZE, ge=1, le=200)  # how many top creators to return and save
    save: bool = True  # False = re-rank only (e.g. flipping the budget toggle); nothing stored
    name: Optional[str] = None
    area: Optional[str] = None
    campaign_objective: Optional[str] = None
    preferred_format: Optional[str] = None
    price_bracket: Optional[str] = None
    vibe: Optional[str] = None


@lru_cache
def get_vocab():
    return {k: set(v) for k, v in json.loads(Path(VOCAB_JSON).read_text(encoding="utf-8")).items()}


@lru_cache
def get_db():
    return db.from_env()


@app.get("/health")
def health():
    return {"status": "ok"}


def _response(brief, sl):
    """API shape for a (cafe_briefs row, shortlists row) pair. Same for new and stored shortlists."""
    supported = sl["scope_message"] is None
    return {
        "brief_id": brief.get("id"),
        "shortlist_id": sl.get("id"),
        "created_at": sl.get("created_at"),
        "supported": supported,
        "message": sl["scope_message"],
        "scored_on": {"city": brief["city"], "tone_preference": brief["tone_preference"],
                      "weights": cfg.WEIGHTS} if supported else None,
        "context_not_used_in_ranking": {k: brief[k] for k in ("name", *db.CONTEXT_COLUMNS) if brief.get(k)},
        "budget": {"preference": brief["budget_preference"], "max_budget_inr": brief["max_budget_inr"],
                   "filter_on": brief["budget_filter_on"], "note": sl["filter_note"],
                   "skipped_higher_ranked": sl.get("skipped") or []},
        "eligible": sl["eligible"],
        "rows": sl["rows"],
    }


@app.get("/vocab")
def vocab_options(vocab=Depends(get_vocab)):
    """Dropdown values for the requirements form (Lists vocabulary)."""
    return {field: sorted(vocab[key]) for field, key in VOCAB_FIELDS.items()}


@app.post("/shortlist")
def create_shortlist(brief: Brief, vocab=Depends(get_vocab), store=Depends(get_db)):
    fields = brief.model_dump(exclude={"budget_filter", "top_n", "save"})
    try:
        req = make_requirements(vocab, **fields)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    result = shortlist(db.load_creators(store), req, brief.budget_filter)
    result["rows"] = result["rows"][:brief.top_n]  # top N after the budget filter; ranking itself unchanged
    skipped = skipped_above(result["hidden"], result["rows"])
    if note := skipped_note(skipped):
        result["filter_note"] = f"{result['filter_note']} {note}"  # saved with the shortlist for outreach
    brief_row, sl_row = db.records(req, brief.budget_filter, result, skipped)
    if brief.save:
        brief_row, sl_row = db.save_shortlist(store, brief_row, sl_row)
    return _response(brief_row, sl_row)


@app.get("/shortlist/{shortlist_id}")
def get_shortlist(shortlist_id: UUID, store=Depends(get_db)):
    found = db.get_shortlist(store, shortlist_id)
    if not found:
        raise HTTPException(status_code=404, detail="shortlist not found")
    return _response(*found)
