import pytest
from fastapi.testclient import TestClient

import api
import seed
from normalize import load_vocab
from scorer import load_pool, rank
from shortlist import make_requirements
from tests.fake_supabase import FakeSupabase


@pytest.fixture(scope="module")
def ctx():
    fake = FakeSupabase()
    store = fake.client()
    store.insert("creators", seed.build_rows(), upsert_on="handle")
    vocab = load_vocab()
    api.app.dependency_overrides = {api.get_db: lambda: store, api.get_vocab: lambda: vocab}
    yield TestClient(api.app), fake, vocab
    api.app.dependency_overrides = {}


def test_pune_brief_returns_ranked_list(ctx):
    client, fake, vocab = ctx
    r = client.post("/shortlist", json={"city": "Pune", "tone_preference": "Aesthetic/Calm", "name": "Green Leaf",
                                         "area": "Baner", "preferred_format": "Reels"})
    assert r.status_code == 200
    body = r.json()
    assert body["supported"] and body["message"] is None and body["eligible"] == 102
    expected = rank(load_pool(), make_requirements(vocab, tone_preference="Aesthetic/Calm"))
    assert body["rows"] == expected[:5]  # top 5 by default
    assert [r["rank"] for r in body["rows"]] == [1, 2, 3, 4, 5]
    first = body["rows"][0]
    assert {"rank", "handle", "final_score", "locality", "content", "engagement", "locality_tier", "confidence",
            "engagement_confidence", "rationale", "rate_band"} <= set(first)
    assert body["context_not_used_in_ranking"]["area"] == "Baner"
    # persisted and retrievable
    assert fake.tables["cafe_briefs"][-1]["tone_preference"] == "Aesthetic/Calm"
    saved = client.get(f"/shortlist/{body['shortlist_id']}").json()
    assert saved == body  # stored shortlist comes back in exactly the POST shape


def test_get_returns_same_shape_with_skipped(ctx):
    client, _, _ = ctx
    body = client.post("/shortlist", json={"tone_preference": "Aesthetic/Calm", "budget_preference": "Paid Only",
                                           "max_budget_inr": 2500, "budget_filter": True, "name": "X"}).json()
    saved = client.get(f"/shortlist/{body['shortlist_id']}").json()
    assert saved == body and saved["created_at"]
    assert [s["rank"] for s in saved["budget"]["skipped_higher_ranked"]] == [1, 3]


def test_save_false_reranks_without_storing(ctx):
    client, fake, _ = ctx
    before = (len(fake.tables["cafe_briefs"]), len(fake.tables["shortlists"]))
    body = client.post("/shortlist", json={"tone_preference": "Fun/Energetic", "save": False}).json()
    assert len(body["rows"]) == 5 and body["shortlist_id"] is None and body["brief_id"] is None
    assert (len(fake.tables["cafe_briefs"]), len(fake.tables["shortlists"])) == before


def test_vocab_endpoint(ctx):
    client, _, vocab = ctx
    body = client.get("/vocab").json()
    assert body["tone_preference"] == sorted(vocab["ContentTonePref"])
    assert set(body) == {"tone_preference", "budget_preference", "campaign_objective", "preferred_format",
                         "price_bracket"}


def test_non_pune_brief_not_supported(ctx):
    client, _, _ = ctx
    r = client.post("/shortlist", json={"city": "Mumbai", "tone_preference": "Fun/Energetic", "budget_filter": True})
    body = r.json()
    assert r.status_code == 200 and body["supported"] is False
    assert body["message"] == "This pilot covers Pune-area creators only. Mumbai isn't supported yet."
    assert body["rows"] == [] and body["eligible"] == 0


def test_budget_filter_via_api(ctx):
    client, _, _ = ctx
    brief = {"tone_preference": "Aesthetic/Calm", "budget_preference": "Paid Only", "max_budget_inr": 2500,
             "top_n": 200}
    off = client.post("/shortlist", json=brief).json()["rows"]
    on = client.post("/shortlist", json={**brief, "budget_filter": True}).json()["rows"]
    assert 0 < len(on) < len(off) and on == [r for r in off if r in on]


def test_top_n_taken_after_budget_filter(ctx):
    client, fake, _ = ctx
    brief = {"tone_preference": "Aesthetic/Calm", "budget_preference": "Paid Only", "max_budget_inr": 2500,
             "budget_filter": True}
    body = client.post("/shortlist", json=brief).json()
    full = client.post("/shortlist", json={**brief, "top_n": 200}).json()["rows"]
    assert body["rows"] == full[:5] and len(body["rows"]) == 5   # best 5 the business can afford
    assert fake.tables["shortlists"][-2]["rows"] == body["rows"]  # saved list is the top 5 too
    assert client.post("/shortlist", json={**brief, "top_n": 0}).status_code == 422


def test_skipped_ranks_and_explanations_reported(ctx):
    client, fake, _ = ctx
    body = client.post("/shortlist", json={"tone_preference": "Aesthetic/Calm", "budget_preference": "Paid Only",
                                           "max_budget_inr": 2500, "budget_filter": True}).json()
    shown = [r["rank"] for r in body["rows"]]
    skipped = body["budget"]["skipped_higher_ranked"]
    assert sorted(shown + [s["rank"] for s in skipped]) == list(range(1, shown[-1] + 1))  # gaps fully explained
    assert all("above the max of Rs 2,500" in s["reason"] for s in skipped)
    assert f"Not shown because of budget: #1 {skipped[0]['handle']}" in body["budget"]["note"]
    assert fake.tables["shortlists"][-1]["filter_note"] == body["budget"]["note"]  # saved for outreach
    for r in body["rows"]:
        assert len(r["explanation"]) == 5 and r["explanation"][0].startswith(f"Overall {round(r['final_score'] * 100)}/100")


def test_no_skipped_note_when_filter_off(ctx):
    client, _, _ = ctx
    body = client.post("/shortlist", json={"tone_preference": "Aesthetic/Calm"}).json()
    assert body["budget"]["skipped_higher_ranked"] == [] and "Not shown" not in body["budget"]["note"]


@pytest.mark.parametrize("brief", [{"city": "Pune"}, {"tone_preference": "Moody"}, {"city": "", "tone_preference": "Fun/Energetic"}])
def test_invalid_brief_rejected(ctx, brief):
    client, _, _ = ctx
    assert client.post("/shortlist", json=brief).status_code == 422


def test_unknown_shortlist_404(ctx):
    client, _, _ = ctx
    assert client.get("/shortlist/00000000-0000-0000-0000-000000000000").status_code == 404
