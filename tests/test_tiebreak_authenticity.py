"""Phase 5 (v2): tie-breaker for near-equal scores, and the authenticity dampener on engagement."""
import random

import pytest

import config as cfg
from scorer import order, rank

TEST_CAFE = {"name": "Test cafe", "city": "Pune", "tone_pref": "Aesthetic/Calm"}


def row(handle, final, tier, locality, engagement=0.5):
    return {"handle": handle, "rationale": "", "explanation": [],
            "_sort": (final, tier, locality, engagement, handle)}


def handles(rows):
    return [r["handle"] for r in rows]


# ---- Tie-breaker -------------------------------------------------------------------------------------------

def test_tie_resolved_verified_over_proxy_then_locality():
    rows = [
        row("@proxy", 0.6000, "Proxy", 0.60),          # top score, but inferred location
        row("@verified_low", 0.5995, "Verified", 0.61),
        row("@verified_high", 0.5992, "Verified", 0.70),
    ]  # all within 0.001 of the top -> one tie
    assert handles(order(rows)) == ["@verified_high", "@verified_low", "@proxy"]


def test_tie_falls_back_to_engagement_then_handle():
    rows = [row("@b", 0.5, "Verified", 0.8, 0.4), row("@c", 0.5, "Verified", 0.8, 0.4),
            row("@a", 0.5, "Verified", 0.8, 0.3), row("@d", 0.5, "Verified", 0.8, 0.9)]
    assert handles(order(rows)) == ["@d", "@b", "@c", "@a"]


def test_tied_rows_get_a_note_untied_rows_dont():
    tied = order([row("@x", 0.5, "Verified", 0.8), row("@y", 0.5004, "Proxy", 0.6)])
    assert all("Tied on score" in r["rationale"] and "Tied on score" in r["explanation"][-1] for r in tied)
    alone = order([row("@x", 0.6, "Verified", 0.8), row("@y", 0.5, "Proxy", 0.6)])
    assert all(r["rationale"] == "" and r["explanation"] == [] for r in alone)


def test_genuinely_different_scores_never_reorder():
    rows = [row("@proxy", 0.70, "Proxy", 0.60), row("@verified", 0.69, "Verified", 1.0)]  # 1 point apart
    assert handles(order(rows)) == ["@proxy", "@verified"]
    # Epsilon is measured from a tie group's top score, so ties never chain past it.
    chain = [row("@a", 0.5000, "Proxy", 0.6), row("@b", 0.4992, "Proxy", 0.6), row("@c", 0.4985, "Verified", 0.9)]
    assert handles(order(chain)) == ["@a", "@b", "@c"]  # c is 0.0015 below a: not tied with a


def test_tie_order_is_reproducible_under_shuffle():
    rows = [row(f"@c{i}", 0.5 + (i % 3) * 0.0003, ["Verified", "Proxy"][i % 2], 0.6 + (i % 4) * 0.01, (i % 5) / 10)
            for i in range(12)]
    first = handles(order([dict(r) for r in rows]))
    for seed in range(5):
        shuffled = [dict(r) for r in rows]
        random.Random(seed).shuffle(shuffled)
        assert handles(order(shuffled)) == first


@pytest.fixture(scope="module")
def pool():
    from scorer import load_pool
    return load_pool()


def test_real_ranking_only_reorders_within_epsilon(pool):
    from scorer import load_cafes
    for cafe in load_cafes().values():
        ranked = rank(pool, cafe)
        for above, below in zip(ranked, ranked[1:]):
            assert above["final_score"] >= below["final_score"] - cfg.TIE_EPSILON - 1e-4  # 4-dp rounding slack


# ---- Authenticity dampener ---------------------------------------------------------------------------------

BASE = {"ER%": 0.05, "content_tone": "Fun/Energetic", "content_category": "Food Review/Taste-Test",
        "Posting Pace Category": "High (every 1-3 days)", "Creator Base Location (City/Area)": "Pune",
        "features_pune": "Yes", "engagement_confidence": "verified"}


def creators_with(reads):
    return [{**BASE, "Username": f"@{i}", "authenticity": a} for i, a in enumerate(reads)]


def test_dampener_scales_engagement_by_config_multiplier():
    reads = ["Looks Genuine", "Some Red Flags", "Likely Inflated", "Not Assessed", None]
    by = {r["handle"]: r for r in rank(creators_with(reads), TEST_CAFE)}
    genuine = by["@0"]["engagement"]
    assert by["@1"]["engagement"] == pytest.approx(genuine * cfg.AUTHENTICITY_MULTIPLIER["Some Red Flags"], abs=1e-4)
    assert by["@2"]["engagement"] == pytest.approx(genuine * cfg.AUTHENTICITY_MULTIPLIER["Likely Inflated"], abs=1e-4)
    assert by["@3"]["engagement"] == genuine and by["@4"]["engagement"] == genuine  # not assessed / missing: neutral
    assert by["@2"]["authenticity_factor"] == 0.7 and by["@0"]["authenticity_factor"] == 1.0


def test_dampener_is_shown_in_rationale_and_explanation():
    by = {r["handle"]: r for r in rank(creators_with(["Looks Genuine", "Likely Inflated"]), TEST_CAFE)}
    assert "authenticity: likely inflated (engagement x0.7)" in by["@1"]["rationale"]
    assert any("authenticity read: Likely Inflated" in line for line in by["@1"]["explanation"])
    assert "authenticity" not in by["@0"]["rationale"]


def test_dampener_applies_before_the_tie_breaker():
    # Identical creators: undampened they tie and '@0' would win on handle. Dampening '@0' (Likely Inflated)
    # lowers its final score below the tie window, so '@1' ranks first on score alone.
    ranked = rank([{**BASE, "Username": "@0", "authenticity": "Likely Inflated"},
                   {**BASE, "Username": "@1", "authenticity": "Looks Genuine"}], TEST_CAFE)
    assert handles(ranked) == ["@1", "@0"]
    assert ranked[0]["final_score"] - ranked[1]["final_score"] > cfg.TIE_EPSILON
    assert all("Tied on score" not in r["rationale"] for r in ranked)
