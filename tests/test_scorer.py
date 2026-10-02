import random

import pytest

import config as cfg
from scorer import load_cafes, load_pool, rank


# Synthetic-creator tests need only a city and tone, not the workbook (they run on CI too).
TEST_CAFE = {"name": "Test cafe", "city": "Pune", "tone_pref": "Aesthetic/Calm"}


@pytest.fixture(scope="module")
def pool():
    return load_pool()


@pytest.fixture(scope="module")
def cafes():
    return load_cafes()


def test_same_input_same_output(pool, cafes):
    for cafe in cafes.values():
        first = rank(pool, cafe)
        assert rank(pool, cafe) == first
        shuffled = pool[:]
        random.Random(42).shuffle(shuffled)
        assert rank(shuffled, cafe) == first  # input order doesn't matter either


def test_proxy_never_outscores_verified_on_locality(pool, cafes):
    for cafe in cafes.values():
        ranked = rank(pool, cafe)
        # Tier 1 = audience data that includes the cafe city (locality > 0).
        verified = [r["locality"] for r in ranked if r["locality_tier"] == "Verified" and r["locality"] > 0]
        proxy = [r["locality"] for r in ranked if r["locality_tier"] == "Proxy"]
        assert verified and proxy
        assert max(proxy) <= cfg.PROXY_CAP <= min(verified)


def test_weakest_verified_beats_strongest_proxy_on_locality():
    base = {"ER%": 0.05, "content_tone": "Fun/Energetic", "content_category": "Food Review/Taste-Test",
            "Posting Pace Category": "High (every 1-3 days)"}
    strong_verified = {**base, "Username": "@v_strong", "City 1": "Pune", "City 1 %": 0.50}
    weak_verified = {**base, "Username": "@v_weak", "City 1": "Pune", "City 1 %": 0.01}
    best_proxy = {**base, "Username": "@p_best", "Creator Base Location (City/Area)": "Pune", "features_pune": "Yes"}
    by_handle = {r["handle"]: r for r in rank([strong_verified, weak_verified, best_proxy], TEST_CAFE)}
    assert by_handle["@v_weak"]["locality"] > by_handle["@p_best"]["locality"]
    assert by_handle["@p_best"]["locality"] == cfg.PROXY_CAP


def test_occasionally_gets_partial_proxy_credit():
    base = {"ER%": 0.05, "content_tone": "Fun/Energetic", "content_category": "Food Review/Taste-Test",
            "Posting Pace Category": "High (every 1-3 days)", "Creator Base Location (City/Area)": "Pune"}
    pool = [{**base, "Username": f"@{v}", "features_pune": v} for v in ("Yes", "Occasionally", "No")]
    loc = {r["handle"]: r["locality"] for r in rank(pool, TEST_CAFE)}
    # raw = (base 1 + features 1 / 0.5 / 0) / 2 -> 1.0 / 0.75 / 0.5, scaled to the 0.6 proxy cap
    assert loc == {"@Yes": 0.6, "@Occasionally": 0.45, "@No": 0.3}


def test_er_outlier_keeps_top_engagement_without_flattening_others(pool, cafes):
    ranked = {r["handle"]: r for r in rank(pool, cafes["Qala Cafe & Co-works"])}
    top_er = max((c for c in pool if c["Username"] in ranked), key=lambda c: c["ER%"])["Username"]  # real 300%+ outlier
    # The p95 ceiling is checked before the authenticity dampener: undo it to see the ceiling's own result.
    pre = {h: r["engagement"] / r["authenticity_factor"] for h, r in ranked.items()}
    assert pre[top_er] == pytest.approx(max(pre.values())) and pre[top_er] == pytest.approx(1.0)

    # ER component alone (engagement minus pace part): a ~12% creator must sit clearly above a ~4% one.
    # Against the raw max (302%) they were ~0.016 apart; against the p95 ceiling they spread out.
    creators = {c["Username"]: c for c in pool if c["Username"] in ranked}
    def er_part(handle):
        pace = cfg.PACE_SCORES.get(creators[handle]["Posting Pace Category"], 0)
        return pre[handle] - cfg.ENGAGEMENT_WEIGHTS["pace"] * pace
    near = lambda target: min(creators, key=lambda h: abs(creators[h]["ER%"] - target))
    assert er_part(near(0.12)) - er_part(near(0.04)) > 0.1


def test_engagement_confidence_carried_to_output(pool, cafes):
    ranked = {r["handle"]: r for r in rank(pool, cafes["Qala Cafe & Co-works"])}
    by = {c["Username"]: c for c in pool}
    high_unverified = [h for h in ranked if by[h]["engagement_confidence"] == "unverified" and by[h]["ER%"] > 0.5]
    assert len(high_unverified) >= 2  # flagged creators with high stored ER are labelled, not hidden
    for h in high_unverified:
        assert ranked[h]["engagement_confidence"] == "unverified"
        assert "unverified (ER not cross-validated)" in ranked[h]["rationale"]
        assert ranked[h]["rank"] > 10  # and don't ride the questionable ER into the top ranks
    first = min(ranked.values(), key=lambda r: r["rank"])
    assert first["engagement_confidence"] == "verified"
    assert "unverified" not in first["rationale"].split("Engagement")[-1]


def test_unverifiable_implausible_er_capped_at_median():
    from validate import validate_er
    base = {"content_tone": "Fun/Energetic", "content_category": "Food Review/Taste-Test", "Followers": "10k",
            "Posting Pace Category": "High (every 1-3 days)", "Creator Base Location (City/Area)": "Pune"}
    creators = [{**base, "Username": f"@normal{i}", "ER%": er, "Engagements": er * 10_000}
                for i, er in enumerate([0.01, 0.02, 0.03, 0.04, 0.05])]
    creators += [
        {**base, "Username": "@implausible", "ER%": 2.5, "Engagements": 0},          # flagged, >100%: capped
        {**base, "Username": "@plausible_flagged", "ER%": 0.08, "Engagements": 0},   # flagged, plausible: normal
    ]
    rows, _ = validate_er(creators)
    ranked = {r["handle"]: r for r in rank(rows, TEST_CAFE)}
    # Pre-cap engagement rises with ER (same pace): normal0..4 < plausible_flagged < implausible -> median of 7 = @normal3
    assert ranked["@implausible"]["engagement_capped"]
    assert ranked["@implausible"]["engagement"] == ranked["@normal3"]["engagement"]
    assert ranked["@implausible"]["engagement"] < ranked["@plausible_flagged"]["engagement"]
    assert not ranked["@plausible_flagged"]["engagement_capped"]
    assert ranked["@plausible_flagged"]["engagement_confidence"] == "unverified"


def test_other_category_accounts_excluded(pool, cafes):
    other = {c["Username"] for c in pool if c["content_category"] == "Other"}
    assert len(other) == 13
    assert sum(c["Content Category"] == "Business / Venue Account" for c in pool if c["Username"] in other) == 11
    ranked = rank(pool, cafes["Buddy Coffee Espresso"])
    assert len(ranked) == len(pool) - len(other)
    assert not other & {r["handle"] for r in ranked}


def test_unmatched_or_unknown_tone_preference_does_not_crash(pool):
    for tone in ["Aesthetic/Calm", "Witty/Comedic", "Not A Real Tone", None]:
        ranked = rank(pool, {"name": "test", "city": "Pune", "tone_pref": tone})
        assert len(ranked) == 102
        if tone not in cfg.CONTENT_MATCH:
            assert all(r["content"] == 0 for r in ranked)
