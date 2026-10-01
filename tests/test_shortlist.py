import pytest

from normalize import load_vocab
from scorer import load_cafes, load_pool, rank
from shortlist import budget_filter, make_requirements, rate_floor, seed_requirements, shortlist


@pytest.fixture(scope="module")
def vocab():
    return load_vocab()


@pytest.fixture(scope="module")
def pool():
    return load_pool()


def test_requirements_rank_identically_to_cafe_profiles(vocab, pool):
    for cafe in load_cafes().values():
        req = make_requirements(vocab, city="Pune", tone_preference=cafe["tone_pref"])
        assert rank(pool, req) == rank(pool, cafe)


def test_context_fields_do_not_affect_ranking(vocab, pool):
    bare = make_requirements(vocab, tone_preference="Aesthetic/Calm")
    full = make_requirements(vocab, tone_preference="Aesthetic/Calm", budget_preference="Paid Only",
                             max_budget_inr=3000, name="X", area="Baner", campaign_objective="Brand Awareness",
                             preferred_format="Reels", price_bracket="Mid (Rs 500-1200 for two)", vibe="calm")
    assert rank(pool, bare) == rank(pool, full)


def test_seed_matches_profile(vocab, pool):
    req = seed_requirements(vocab, "Qala Cafe & Co-works")
    assert req["context"]["area"] == "Baner" and rank(pool, req) == rank(pool, load_cafes()["Qala Cafe & Co-works"])


def test_budget_filter_only_removes_rows(vocab, pool):
    req = make_requirements(vocab, tone_preference="Aesthetic/Calm", budget_preference="Paid Only", max_budget_inr=2000)
    ranked = rank(pool, req)
    visible, _ = budget_filter(ranked, req, enabled=True)
    assert 0 < len(visible) < len(ranked)
    assert visible == [r for r in ranked if r in visible]           # same order, rows untouched
    assert all(rate_floor(r["rate_band"]) <= 2000 for r in visible)
    assert budget_filter(ranked, req, enabled=False)[0] == ranked    # default off: everyone


@pytest.mark.parametrize("pref", ["Open to Either", "Not Yet Decided"])
def test_budget_filter_noop_for_undecided(vocab, pool, pref):
    req = make_requirements(vocab, tone_preference="Fun/Energetic", budget_preference=pref, max_budget_inr=1000)
    ranked = rank(pool, req)
    assert budget_filter(ranked, req, enabled=True)[0] == ranked


def test_barter_only_does_not_filter(vocab, pool):
    # No barter signal in creator data yet: filtering would hide all 102, so Barter Only is a no-op with a note.
    req = make_requirements(vocab, tone_preference="Fun/Energetic", budget_preference="Barter Only", max_budget_inr=1000)
    ranked = rank(pool, req)
    visible, note = budget_filter(ranked, req, True)
    assert visible == ranked and "no barter data" in note


def test_creators_without_estimate_never_hidden(vocab, pool):
    req = make_requirements(vocab, tone_preference="Fun/Energetic", budget_preference="Paid Only", max_budget_inr=1000)
    ranked = rank(pool, req)
    visible, note = budget_filter(ranked + [{**ranked[0], "handle": "@no_estimate", "rate_band": None}], req, True)
    assert [r["handle"] for r in visible] == ["@no_estimate"] and "ESTIMATED" in note


@pytest.mark.parametrize("fields, msg", [
    ({"tone_preference": None}, "tone_preference is required"),
    ({"city": "  ", "tone_preference": "Fun/Energetic"}, "city is required"),
    ({"tone_preference": "Moody"}, "not in"),
    ({"tone_preference": "Fun/Energetic", "budget_preference": "Cheap"}, "not in"),
    ({"tone_preference": "Fun/Energetic", "preferred_format": "Billboard"}, "not in"),
])
def test_invalid_requirements_rejected(vocab, fields, msg):
    with pytest.raises(ValueError, match=msg):
        make_requirements(vocab, **fields)


def test_non_pune_city_returns_not_supported_and_no_creators(vocab, pool):
    req = make_requirements(vocab, city="Mumbai", tone_preference="Fun/Energetic")  # accepted by the form
    result = shortlist(pool, req, budget_filter_on=True)
    assert result["message"] == "This pilot covers Pune-area creators only. Mumbai isn't supported yet."
    assert result["rows"] == [] and result["eligible"] == 0


def test_pune_city_returns_normal_ranked_list(vocab, pool):
    req = make_requirements(vocab, city="pune", tone_preference="Fun/Energetic")
    result = shortlist(pool, req)
    assert result["message"] is None
    assert result["rows"] == rank(pool, req) and len(result["rows"]) == 102


def test_rate_floor():
    assert rate_floor("₹2,500–₹5,000 indicative; public rate card not found") == 2500
    assert rate_floor(None) is None and rate_floor("Unknown/Not Shared") is None
