import json
import os

import pytest

import db
import seed
from normalize import load_creators as load_raw_creators, load_vocab
from scorer import load_cafes, load_pool, rank
from shortlist import make_requirements, shortlist
from tests.fake_supabase import FakeSupabase
from validate import validate_er


@pytest.fixture(scope="module")
def rows():
    return seed.build_rows()


@pytest.fixture(scope="module")
def seeded(rows):
    fake = FakeSupabase()
    client = fake.client()
    client.insert("creators", rows, upsert_on="handle")
    return fake, client


def test_scorer_from_supabase_equals_scorer_from_file(seeded):
    _, client = seeded
    file_pool, db_pool = load_pool(), db.load_creators(client)
    assert len(db_pool) == len(file_pool) == 115
    for cafe in load_cafes().values():
        assert rank(db_pool, cafe) == rank(file_pool, cafe)
    req = make_requirements(load_vocab(), tone_preference="Aesthetic/Calm", budget_preference="Paid Only",
                            max_budget_inr=2500)
    assert shortlist(db_pool, req, True) == shortlist(file_pool, req, True)


@pytest.mark.needs_data
def test_seed_excludes_pii():
    # The workbook's PII columns are currently empty, so plant PII to prove it can never reach the DB.
    raw = load_raw_creators()
    for i, c in enumerate(raw):
        c.update({"Email Address": f"pii{i}@example.com", "Phone Number": f"+91-98765-{i:05d}",
                  "Address": f"{i} Secret Lane, Pune"})
    rows = seed.build_rows(raw)
    fake = FakeSupabase()
    fake.client().insert("creators", rows, upsert_on="handle")
    sent = b"".join(r.content for r in fake.requests if r.method == "POST").decode()

    assert all(set(r) == set(db.CREATOR_FIELDS) | {"audience_cities"} for r in rows)
    assert not any(w in key.lower() for r in rows for key in r for w in ("email", "phone", "address"))
    assert "@example.com" not in sent and "+91-98765" not in sent and "Secret Lane" not in sent
    assert fake.tables["creators"] and all("Email Address" not in r for r in fake.tables["creators"])


def test_engagement_confidence_and_locality_preserved(rows):
    raw = {c["Username"]: c for c in load_raw_creators()}
    _, decisions = validate_er(raw.values())
    flagged = {d["handle"] for d in decisions if d["action"] == "flagged"}
    for r in rows:  # confidence flag survives seeding for every creator
        assert r["engagement_confidence"] == ("unverified" if r["handle"] in flagged else "verified")
        src = raw[r["handle"]]
        if src.get("City 1"):  # audience cities survive in order
            assert r["audience_cities"][0] == [src["City 1"], src["City 1 %"]]
    assert json.loads(json.dumps(rows)) == rows  # JSON round-trip safe


@pytest.mark.needs_data
@pytest.mark.skipif(not os.getenv("SUPABASE_URL"), reason="live Supabase not configured")
def test_live_supabase_matches_file():
    live_pool = db.load_creators(db.from_env())
    for cafe in load_cafes().values():
        assert rank(live_pool, cafe) == rank(load_pool(), cafe)
