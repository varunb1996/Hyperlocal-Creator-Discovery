"""Deterministic creator -> cafe scorer. Same input, same output. No LLM.

Logic translated from Matching_Engine.xlsx 'Scorer' tab, with one deliberate change:
locality tiers occupy separate bands (verified in [PROXY_CAP, 1], proxy in [0, PROXY_CAP]),
so an inferred guess can never outrank a measured audience.
"""
import argparse
import logging
import statistics

from openpyxl import load_workbook

import config as cfg
from normalize import CREATORS_XLSX, load_creators, load_mappings, load_vocab, normalize
from validate import validate_er

log = logging.getLogger(__name__)

AUDIENCE_CITIES = [(f"City {i}", f"City {i} %") for i in range(1, 6)]
BASE_LOCATION = "Creator Base Location (City/Area)"


def load_cafes(creators_xlsx=CREATORS_XLSX):
    """{cafe name: {name, city, tone_pref}} from the 'Cafe Profiles' sheet."""
    ws = load_workbook(creators_xlsx, read_only=True, data_only=True)["Cafe Profiles"]
    rows = ws.iter_rows(values_only=True)
    headers = next(rows)
    cafes = {}
    for r in rows:
        row = dict(zip(headers, r))
        if row.get("Establishment Name"):
            name = row["Establishment Name"].strip()
            cafes[name] = {"name": name, "city": cfg.DEFAULT_CAFE_CITY,
                           "tone_pref": row.get("Content Tone Preference"), "profile": row}
    return cafes


def is_eligible(creator):
    """Completeness check, then explicit category exclusion. Logs every exclusion."""
    missing = [f for f in cfg.REQUIRED_FIELDS if creator.get(f) in (None, "")]
    if missing:
        log.info("EXCLUDED %s: missing %s", creator.get("Username"), missing)
        return False
    if creator["content_category"] in cfg.EXCLUDED_CATEGORIES:
        log.info("EXCLUDED %s: content category %r (%s)", creator["Username"],
                 creator["content_category"], creator.get("Content Category"))
        return False
    return True


def _raw_locality(creator, city):
    """(tier, raw score). Verified raw = audience share in city; proxy raw = avg proxy points."""
    audience = [(creator.get(c), creator.get(p)) for c, p in AUDIENCE_CITIES if creator.get(c)]
    if audience:
        return "Verified", sum(p or 0 for c, p in audience if c.strip().lower() == city.lower())
    base = creator.get(BASE_LOCATION) or ""
    features = cfg.FEATURES_CREDIT.get(creator.get("features_pune"), 0.0) \
        if city.lower() == cfg.FEATURES_COLUMN_CITY.lower() else 0.0
    if base or features:
        points = (cfg.PROXY_POINTS_BASE_CITY if city.lower() in base.lower() else 0) \
            + cfg.PROXY_POINTS_FEATURES_CITY * features
        return "Proxy", points / 2
    return "Unknown", 0.0


def _er_ceiling(ers):
    """ER_CEILING_PERCENTILE of the pool (inclusive/linear interpolation, as Excel PERCENTILE.INC)."""
    if len(ers) < 2:
        return max(ers, default=0)
    return statistics.quantiles(ers, n=100, method="inclusive")[cfg.ER_CEILING_PERCENTILE - 1]


def _band(value, bands):
    return next(label for threshold, label in bands if value >= threshold)


def _rationale(creator, cafe, tier, content, engagement):
    city = cafe["city"]
    if tier == "Verified":
        loc = f"Verified local audience in {city}" if creator["_raw_loc"] > 0 \
            else f"Verified audience data shows no {city} share"
    elif tier == "Proxy":
        feat = {"Yes": f"features {city} venues; ",
                "Occasionally": f"occasionally features {city} venues; "}.get(creator.get("features_pune"), "")
        loc = f"Local relevance INFERRED ({feat}base: {creator.get(BASE_LOCATION)}) - unverified"
    else:
        loc = "Local audience unknown"
    eng_note = ""
    if creator.get("engagement_confidence", "unverified") == "unverified":
        eng_note = " - unverified (ER not cross-validated)"
        if creator["_capped"]:
            eng_note += ", capped at pool median (implausible ER)"
    if creator["_auth"] < 1:
        eng_note += f" - authenticity: {creator.get('authenticity', '').lower()} (engagement x{creator['_auth']:g})"
    return (f"{creator.get('Creator')} - {loc}. "
            f"Content {_band(content, cfg.CONTENT_BANDS)} matches cafe tone "
            f"({creator['content_tone']} vs {cafe['tone_pref']}). "
            f"Engagement {_band(engagement, cfg.ENGAGEMENT_BANDS)}{eng_note}.")


def _explanation(creator, cafe, tier, final, locality, content, engagement):
    """Business-facing, plain-language breakdown of already-computed scores. Describes; never changes them."""
    city, w = cafe["city"], cfg.WEIGHTS
    pts = lambda x: round(x * 100)  # shown on a 100-point scale; the scores themselves stay 0-1
    lines = [f"Overall {pts(final)}/100 = {w['locality']}% location fit ({pts(locality)}) + "
             f"{w['content']}% content fit ({pts(content)}) + {w['engagement']}% engagement ({pts(engagement)})."]
    if tier == "Verified" and creator["_raw_loc"] > 0:
        lines.append(f"Location fit {pts(locality)}/100 - measured: {creator['_raw_loc']:.0%} of this creator's audience "
                     f"is in {city}. Measured creators score {pts(cfg.PROXY_CAP)}-100 so they always rank above "
                     f"inferred ones; the strongest {city} audience in the pool scores 100. High confidence.")
    elif tier == "Verified":
        lines.append(f"Location fit 0/100 - measured: {city} is not among this creator's top audience cities.")
    elif tier == "Proxy":
        base = creator.get(BASE_LOCATION) or ""
        reasons = [f"based in {city}" if city.lower() in base.lower() else f"base location: {base or 'unknown'}",
                   {"Yes": f"regularly features {city} venues", "Occasionally": f"occasionally features {city} venues"}
                   .get(creator.get("features_pune"), f"no record of featuring {city} venues")]
        lines.append(f"Location fit {pts(locality)}/100 - inferred, not measured (no audience-location data): "
                     f"{'; '.join(reasons)}. Low confidence; inferred creators always score below measured ones.")
    else:
        lines.append("Location fit 0/100 - no location data available for this creator.")
    lines.append(f"Content fit {pts(content)}/100 - creator's style is {creator['content_tone']}; you asked for "
                 f"{cafe['tone_pref']} ({_band(content, cfg.CONTENT_BANDS).removesuffix('ly')} match).")
    eng = (f"Engagement {pts(engagement)}/100 - engagement rate {creator['ER%']:.1%}, "
           f"posting pace {creator['Posting Pace Category']}.")
    if creator.get("engagement_confidence", "unverified") == "verified":
        eng += " Engagement data cross-checked."
    else:
        eng += " Engagement rate could not be cross-checked against the creator's other numbers - treat with caution."
        if creator["_capped"]:
            eng += " Capped at the pool median because the reported rate is implausible."
    if creator["_auth"] < 1:
        eng += (f" Audience authenticity read: {creator.get('authenticity')}, so engagement is scaled by "
                f"{creator['_auth']:g} (an estimate, so a modest adjustment).")
    lines.append(eng)
    rate = (creator.get("Rate Band") or "").split(" indicative")[0]
    lines.append(f"Estimated rate {rate} per collaboration - indicative only; no public rate card found."
                 if rate else "No rate estimate available.")
    return lines


def rank(creators, cafe):
    """Ranked list of eligible creators for one cafe. Pure function of its inputs."""
    pool = [dict(c) for c in creators if is_eligible(c)]
    if cafe["tone_pref"] not in cfg.CONTENT_MATCH:
        log.warning("Cafe %r tone preference %r not in content-match table; content scores 0",
                    cafe["name"], cafe["tone_pref"])

    for c in pool:
        c["_tier"], c["_raw_loc"] = _raw_locality(c, cafe["city"])
    best = {t: max((c["_raw_loc"] for c in pool if c["_tier"] == t), default=0) for t in ("Verified", "Proxy")}
    er_ceiling = _er_ceiling([c["ER%"] for c in pool])
    for c in pool:
        c["_eng"] = (cfg.ENGAGEMENT_WEIGHTS["er"] * (min(c["ER%"] / er_ceiling, 1.0) if er_ceiling else 0)
                     + cfg.ENGAGEMENT_WEIGHTS["pace"] * cfg.PACE_SCORES.get(c["Posting Pace Category"], 0.0))
    # Guardrail: an unverifiable, implausible ER can't lift a creator above the pool's median engagement.
    median_eng = statistics.median(c["_eng"] for c in pool) if pool else 0.0
    for c in pool:
        c["_capped"] = bool(c.get("er_implausible")) and c["_eng"] > median_eng
        if c["_capped"]:
            log.warning("ENGAGEMENT CAPPED %s: unverified implausible ER %s, engagement %.4f -> pool median %.4f",
                        c["Username"], c["ER%"], c["_eng"], median_eng)
            c["_eng"] = median_eng
    # Authenticity dampener (after the cap, before ranking): a questionable audience nudges engagement down.
    for c in pool:
        c["_auth"] = cfg.AUTHENTICITY_MULTIPLIER.get(c.get("authenticity"), 1.0)
        c["_eng"] *= c["_auth"]

    w = cfg.WEIGHTS
    results = []
    for c in pool:
        tier, raw = c["_tier"], c["_raw_loc"]
        if tier == "Verified":
            locality = cfg.PROXY_CAP + (1 - cfg.PROXY_CAP) * raw / best["Verified"] if raw > 0 else 0.0
        elif tier == "Proxy":
            locality = cfg.PROXY_CAP * raw / best["Proxy"] if best["Proxy"] else 0.0
        else:
            locality = 0.0
        content = cfg.CONTENT_MATCH.get(c["content_tone"], {}).get(cafe["tone_pref"], 0.0)
        engagement = c["_eng"]
        final = (w["locality"] * locality + w["content"] * content + w["engagement"] * engagement) / 100
        results.append({
            "handle": c["Username"],
            "final_score": round(final, 4),
            "locality": round(locality, 4),
            "content": round(content, 4),
            "engagement": round(engagement, 4),
            "locality_tier": tier,
            "confidence": {"Verified": "High", "Proxy": "Low (inferred)", "Unknown": "Unknown"}[tier],
            "engagement_confidence": c.get("engagement_confidence", "unverified"),
            "engagement_capped": c["_capped"],
            "authenticity": c.get("authenticity"),
            "authenticity_factor": c["_auth"],
            "rate_band": c.get("Rate Band"),  # display/filter only, not scored
            "rationale": _rationale(c, cafe, tier, content, engagement),
            "explanation": _explanation(c, cafe, tier, final, locality, content, engagement),
            "_sort": (final, tier, locality, engagement, c["Username"]),
        })

    ranked = order(results)
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
        del r["_sort"]
    return ranked


def _tie_key(r):
    """Within a tie: measured location first, then location fit, engagement, handle A-Z."""
    _, tier, locality, engagement, handle = r["_sort"]
    tiers = cfg.TIE_TIER_ORDER
    return (tiers.index(tier) if tier in tiers else len(tiers), -locality, -engagement, handle)


def order(rows):
    """Rows by final score, highest first. Scores within TIE_EPSILON of a group's top score are a tie, ordered by
    _tie_key; every member of a tie is within epsilon of every other, so genuinely different scores never swap.
    Rows carry `_sort` = (final, tier, locality, engagement, handle) unrounded; tied rows get a note."""
    rows = sorted(rows, key=lambda r: (-r["_sort"][0], _tie_key(r)))
    out, i = [], 0
    while i < len(rows):
        top, j = rows[i]["_sort"][0], i
        while j < len(rows) and top - rows[j]["_sort"][0] <= cfg.TIE_EPSILON + 1e-12:
            j += 1
        group = sorted(rows[i:j], key=_tie_key)
        if len(group) > 1:
            note = (f"Tied on score with {len(group) - 1} other creator(s) (within {cfg.TIE_EPSILON * 100:g} points); "
                    f"order set by measured location first, then location fit, engagement and handle.")
            for g in group:
                g["rationale"] += f" {note}"
                g["explanation"] = [*g["explanation"], note]
        out += group
        i = j
    return out


def load_pool():
    """Phase 1 normalized creators, with Phase 3 ER validation applied."""
    creators, _ = validate_er(normalize(load_creators(), load_mappings(load_vocab())))
    return creators


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cafes = load_cafes()
    parser = argparse.ArgumentParser(description="Rank creators for a cafe.")
    parser.add_argument("cafe", choices=sorted(cafes), help="cafe name (Establishment Name)")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    cafe = cafes[args.cafe]
    ranked = rank(load_pool(), cafe)
    print(f"\n{cafe['name']} ({cafe['city']}, tone: {cafe['tone_pref']}) - {len(ranked)} eligible creators\n")
    print(f"{'#':>3}  {'handle':<28}{'final':>7}{'loc':>7}{'cont':>7}{'eng':>7}  {'locality':<24}engagement")
    for r in ranked[:args.top]:
        eng_flag = r["engagement_confidence"] + (" (capped)" if r["engagement_capped"] else "")
        print(f"{r['rank']:>3}  {r['handle']:<28}{r['final_score']:>7.3f}{r['locality']:>7.3f}"
              f"{r['content']:>7.3f}{r['engagement']:>7.3f}  "
              f"{r['locality_tier'] + '/' + r['confidence']:<24}{eng_flag}")
        print(f"     {r['rationale']}")
