import logging

import pytest

from normalize import load_creators
from validate import parse_count, validate_er


@pytest.fixture(scope="module")
def validated():
    raw = load_creators()
    rows, decisions = validate_er(raw)
    return ({c["Username"]: c for c in raw}, {r["Username"]: r for r in rows},
            {d["handle"]: d for d in decisions})


# Creators are picked by their data, never by name, so no real handles live in the repo.

def test_real_outlier_untouched(validated):
    # The highest stored ER in the pool (>100%) is backed by its own engagements/followers: leave it alone.
    raw, rows, decisions = validated
    top = max(raw, key=lambda h: raw[h]["ER%"] or 0)
    assert raw[top]["ER%"] > 1 and top not in decisions
    assert rows[top]["ER%"] == raw[top]["ER%"]


def test_no_arbiter_clear_outlier_corrected(validated):
    # Exactly one creator has an impossible ER with no likes/comments to arbitrate: corrected to eng/followers.
    raw, rows, decisions = validated
    clear = [d for d in decisions.values() if d["action"] == "corrected" and d["likes_comments_er"] is None]
    assert len(clear) == 1
    d = clear[0]
    assert raw[d["handle"]]["ER%"] > 1 and rows[d["handle"]]["ER%"] == d["eng_per_follower"] < 0.2


def test_arbiter_backs_engagements_column(validated):
    _, rows, decisions = validated
    backed = [d for d in decisions.values() if d["reason"] == "likes+comments backs engagements/followers"]
    assert backed
    assert all(rows[d["handle"]]["ER%"] == d["eng_per_follower"] for d in backed)


def test_arbiter_backs_stored_er_over_corrupt_engagements(validated):
    # Kept: likes+comments agree with stored ER even when the engagements column is wildly off (e.g. 160% vs 12%).
    raw, rows, decisions = validated
    kept = [d for d in decisions.values() if d["action"] == "kept"]
    assert kept and all(rows[d["handle"]]["ER%"] == raw[d["handle"]]["ER%"] for d in kept)
    assert any(d["eng_per_follower"] > 10 * d["stored"] for d in kept)


def test_no_arbiter_moderate_disagreement_flagged_not_changed(validated):
    # High but not impossible stored ERs with no arbiter are flagged for review, never overridden.
    raw, rows, decisions = validated
    flagged_high = [d for d in decisions.values() if d["action"] == "flagged" and d["likes_comments_er"] is None
                    and d["stored"] and 0.5 < d["stored"] <= 1]
    assert len(flagged_high) >= 2
    assert all(rows[d["handle"]]["ER%"] == raw[d["handle"]]["ER%"] for d in flagged_high)


def test_zero_er_filled_never_overrides(validated):
    raw, rows, decisions = validated
    filled = [h for h, d in decisions.items() if d["action"] == "filled"]
    assert len(filled) == 11
    assert all(raw[h]["ER%"] == 0 and rows[h]["ER%"] > 0 for h in filled)


def test_inconsistent_arbiter_is_flagged_not_used(caplog):
    # likes+comments backs eng/followers, but 5000 likes on 1000 plays is itself corrupt -> no forced correction.
    creator = {"Username": "@bad_arbiter", "ER%": 0.02, "Followers": "10k", "Engagements": 1000,
               "Avg. Likes": 1000, "Avg. Comments": 0, "Avg. Reel Plays": 1000}
    with caplog.at_level(logging.WARNING):
        rows, decisions = validate_er([creator])
    assert decisions[0]["action"] == "flagged" and rows[0]["ER%"] == 0.02
    assert "inconsistent with plays" in caplog.text


def test_missing_inputs_flagged_not_guessed():
    creators = [
        {"Username": "@no_followers", "ER%": 1.5, "Followers": None, "Engagements": 500},
        {"Username": "@no_engagements", "ER%": 1.5, "Followers": "10k", "Engagements": 0},
    ]
    rows, decisions = validate_er(creators)
    assert [d["action"] for d in decisions] == ["flagged", "flagged"]
    assert [r["ER%"] for r in rows] == [1.5, 1.5]


def test_rule_is_general_not_hardcoded():
    rows, decisions = validate_er([{"Username": "@anyone", "ER%": 2.0, "Followers": "10k", "Engagements": 1000}])
    assert rows[0]["ER%"] == 0.1 and decisions[0]["action"] == "corrected"


def test_parse_count():
    assert parse_count("17.9k") == 17900 and parse_count("1.2M") == 1_200_000 and parse_count(8100) == 8100
    assert parse_count(None) is None and parse_count("n/a") is None
