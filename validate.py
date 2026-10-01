"""Data validation: resolve ER% corruption within a single scrape.

Stored ER% should equal engagements / followers. Where they disagree, neither column is trusted
wholesale: avg likes + comments is the independent arbiter, but only when it is itself consistent
with the creator's views / reel plays. Every non-trivial decision is logged and returned.

Actions: corrected (value replaced), filled (ER was 0 = not captured), kept (arbiter confirms
stored ER), flagged (left as-is, manual review).
"""
import logging

import config as cfg

log = logging.getLogger(__name__)

_SUFFIX = {"k": 1e3, "m": 1e6}


def parse_count(value):
    """'17.9k' -> 17900.0, 1200 -> 1200.0. Unparseable/blank -> None."""
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value or "").strip().lower().replace(",", "")
    try:
        return float(s[:-1]) * _SUFFIX[s[-1]] if s and s[-1] in _SUFFIX else float(s)
    except ValueError:
        return None


def _close(a, ref):
    return abs(a - ref) <= cfg.ER_REVIEW_TOLERANCE * ref


def _implausible(stored, eng_er):
    """Clear-outlier test: ER above 100%, or above 10x engagements/followers."""
    return bool(stored) and (stored > cfg.ER_IMPLAUSIBLE or bool(eng_er) and stored > cfg.ER_INFLATION_FACTOR * eng_er)


def _arbiter(row, followers):
    """(likes+comments implied ER or None, is it consistent with views/plays?, reason)."""
    likes, comments = parse_count(row.get("Avg. Likes")), parse_count(row.get("Avg. Comments"))
    if likes is None and comments is None:
        return None, False, "no likes/comments data"
    lc = (likes or 0) + (comments or 0)
    plays = parse_count(row.get("Avg. Reel Plays")) or parse_count(row.get("Avg. Views"))
    if not plays:
        return lc / followers, False, "likes+comments cannot be cross-checked (no views/plays)"
    lo, hi = cfg.ARBITER_LC_PER_PLAY
    ratio = lc / plays
    if not lo <= ratio <= hi:
        return lc / followers, False, f"likes+comments inconsistent with plays ({ratio:.4f} per play)"
    return lc / followers, True, "likes+comments consistent with plays"


def _decide(row):
    """(action or None, new ER, eng/followers, likes+comments ER, reason). None = consistent, untouched."""
    stored = row.get("ER%")
    followers, engagements = parse_count(row.get("Followers")), parse_count(row.get("Engagements"))
    if not (followers and followers > 0):
        return "flagged", stored, None, None, "followers missing/zero - cannot verify"
    eng_er = engagements / followers if engagements and engagements > 0 else None
    lc_er, arbiter_ok, why = _arbiter(row, followers)

    if not stored:  # 0 / blank in a single scrape = not captured
        if arbiter_ok:
            return "filled", lc_er, eng_er, lc_er, f"ER not captured; filled from likes+comments ({why})"
        if eng_er:
            return "filled", eng_er, eng_er, lc_er, f"ER not captured; filled from engagements/followers ({why})"
        return "flagged", stored, eng_er, lc_er, "ER and engagements both not captured"
    if eng_er is None:
        return "flagged", stored, eng_er, lc_er, "engagements not captured - cannot verify stored ER"
    if _close(stored, eng_er):
        return None, stored, eng_er, lc_er, ""

    # Disputed: stored ER vs engagements/followers disagree by > tolerance.
    if lc_er is not None:
        if not arbiter_ok:
            return "flagged", stored, eng_er, lc_er, why
        backs_stored, backs_eng = _close(stored, lc_er), _close(eng_er, lc_er)
        if backs_eng and (not backs_stored or abs(eng_er - lc_er) < abs(stored - lc_er)):
            return "corrected", eng_er, eng_er, lc_er, "likes+comments backs engagements/followers"
        if backs_stored:
            return "kept", stored, eng_er, lc_er, "likes+comments backs stored ER"
        return "flagged", stored, eng_er, lc_er, "likes+comments backs neither value"
    if _implausible(stored, eng_er):
        return "corrected", eng_er, eng_er, lc_er, "no arbiter; stored ER is a clear outlier"
    return "flagged", stored, eng_er, lc_er, "no arbiter; disagreement not extreme enough to override"


def validate_er(creators):
    """Return (copies of creators with ER resolved, list of per-creator decisions).

    Each row gains engagement_confidence ("verified" / "unverified" = flagged) and
    er_implausible (flagged AND fails the clear-outlier test; the scorer caps these).
    """
    out, decisions = [], []
    for creator in creators:
        row = dict(creator)
        action, value, eng_er, lc_er, reason = _decide(row)
        row["engagement_confidence"] = "unverified" if action == "flagged" else "verified"
        row["er_implausible"] = action == "flagged" and _implausible(row.get("ER%"), eng_er)
        if action:
            stored = row.get("ER%")
            if action in ("corrected", "filled"):
                row["ER%"] = round(value, 4)
            d = {"handle": row.get("Username"), "action": action, "stored": stored,
                 "eng_per_follower": None if eng_er is None else round(eng_er, 4),
                 "likes_comments_er": None if lc_er is None else round(lc_er, 4),
                 "final": row["ER%"], "reason": reason}
            decisions.append(d)
            (log.warning if action == "flagged" else log.info)(
                "ER %s %s: stored=%s eng/followers=%s likes+comments=%s -> %s (%s)", action.upper(),
                d["handle"], d["stored"], d["eng_per_follower"], d["likes_comments_er"], d["final"], reason)
        out.append(row)
    return out, decisions
