"""Generic HoReCa requirements -> ranked creator shortlist.

Scoring is scorer.rank(), unchanged: only city and tone_preference reach it. Budget is a
view filter on ESTIMATED creator rates (hides rows, never rescores/reorders). Context fields
are carried through for display only. Any city is accepted, but only the pilot city is ranked.
"""
import argparse
import logging
import re
import sys

import config as cfg
from normalize import load_vocab
from scorer import load_cafes, load_pool, rank

NO_BUDGET_EFFECT = {"Open to Either", "Not Yet Decided"}
CONTEXT_VOCAB = {"campaign_objective": "CampaignObjective", "preferred_format": "PreferredFormat",
                 "price_bracket": "PriceBracket"}


def make_requirements(vocab, city=cfg.DEFAULT_CAFE_CITY, tone_preference=None,
                      budget_preference="Not Yet Decided", max_budget_inr=None, **context):
    """Validated requirements dict. Raises ValueError on missing city/tone or off-vocabulary values.

    context: name, area, campaign_objective, preferred_format, price_bracket, vibe (display only).
    """
    city = (city or "").strip()
    if not city:
        raise ValueError("city is required")
    if not tone_preference:
        raise ValueError("tone_preference is required")
    if tone_preference not in vocab["ContentTonePref"]:
        raise ValueError(f"tone_preference {tone_preference!r} not in {sorted(vocab['ContentTonePref'])}")
    budget_preference = budget_preference or "Not Yet Decided"
    if budget_preference not in vocab["BudgetPreference"]:
        raise ValueError(f"budget_preference {budget_preference!r} not in {sorted(vocab['BudgetPreference'])}")
    if max_budget_inr is not None and max_budget_inr <= 0:
        raise ValueError("max_budget_inr must be a positive amount")
    unknown = set(context) - {"name", "area", "vibe", *CONTEXT_VOCAB}
    if unknown:
        raise ValueError(f"unknown fields: {sorted(unknown)}")
    for field, key in CONTEXT_VOCAB.items():
        if context.get(field) and context[field] not in vocab[key]:
            raise ValueError(f"{field} {context[field]!r} not in {sorted(vocab[key])}")
    return {"name": context.get("name") or "(unnamed business)", "city": city, "tone_pref": tone_preference,
            "budget_preference": budget_preference, "max_budget_inr": max_budget_inr,
            "context": {k: v for k, v in context.items() if v}}


def seed_requirements(vocab, cafe_name):
    """Requirements prefilled from a Cafe Profiles row (seed example)."""
    cafe = load_cafes()[cafe_name]
    p = cafe["profile"]
    return make_requirements(
        vocab, city=cafe["city"], tone_preference=cafe["tone_pref"],
        budget_preference=p.get("Budget / Barter Preference"),
        name=cafe["name"], area=p.get("Locality"), campaign_objective=p.get("Campaign Objective"),
        preferred_format=p.get("Preferred Content Format"), price_bracket=p.get("Price Point (Avg Bill for Two)"),
        vibe=p.get("Vibe & Atmosphere"))


def out_of_scope(req):
    """Not-supported message for cities outside the pilot, else None. Hard boundary: no list is produced."""
    if req["city"].lower() != cfg.PILOT_CITY.lower():
        return f"This pilot covers {cfg.PILOT_CITY}-area creators only. {req['city']} isn't supported yet."
    return None


def rate_floor(rate_band):
    """Low end of an estimated range like '₹2,500–₹5,000 indicative' -> 2500. Unparseable -> None."""
    amounts = re.findall(r"₹\s*([\d,]+)", rate_band or "")
    return int(amounts[0].replace(",", "")) if amounts else None


def budget_filter(ranked, req, enabled):
    """(visible rows, note). Only removes rows; order, ranks and scores of the rest are untouched."""
    pref, cap = req["budget_preference"], req["max_budget_inr"]
    if not enabled:
        return ranked, "Budget filter OFF - showing all creators."
    if pref in NO_BUDGET_EFFECT:
        return ranked, f"Budget filter ON but budget preference is {pref!r} - no effect."
    if pref == "Barter Only":
        # Creator data has no barter signal (every creator has a paid estimate), so filtering would hide everyone.
        return ranked, ("Budget filter ON but there's no barter data on creators yet - no effect. "
                        "Rates shown are paid estimates.")
    if cap is None:
        return ranked, "Budget filter ON but no max spend per creator set - no effect."
    visible = [r for r in ranked if (f := rate_floor(r["rate_band"])) is None or f <= cap]
    return visible, (f"Budget filter ON (max Rs {cap:,} per creator) - filtering on ESTIMATED rates "
                     f"(public rate cards not found); "
                     f"hid {len(ranked) - len(visible)} creator(s) whose lowest estimate exceeds budget. "
                     f"Creators with no estimate are never hidden.")


def _hidden_reason(row, req):
    return (f"lowest estimated rate Rs {rate_floor(row['rate_band']):,} is above the max of "
            f"Rs {req['max_budget_inr']:,}")


def shortlist(pool, req, budget_filter_on=False):
    """{message, eligible, rows, hidden, filter_note}. Out-of-scope city -> message set, no creators, no scores.

    hidden: creators removed by the budget filter, each with its original rank and the reason.
    """
    if message := out_of_scope(req):
        return {"message": message, "eligible": 0, "rows": [], "hidden": [], "filter_note": None}
    ranked = rank(pool, req)
    rows, filter_note = budget_filter(ranked, req, budget_filter_on)
    shown = {r["rank"] for r in rows}
    hidden = [{"rank": r["rank"], "handle": r["handle"], "rate_band": r["rate_band"],
               "reason": _hidden_reason(r, req)} for r in ranked if r["rank"] not in shown]
    return {"message": None, "eligible": len(ranked), "rows": rows, "hidden": hidden, "filter_note": filter_note}


def skipped_above(hidden, shown_rows):
    """Budget-hidden creators that ranked above the last creator shown (the gaps in the shown ranks)."""
    last = shown_rows[-1]["rank"] if shown_rows else 0
    return [h for h in hidden if h["rank"] < last]


def skipped_note(skipped):
    """Readable note naming the skipped higher-ranked creators, or None."""
    if not skipped:
        return None
    return "Not shown because of budget: " + "; ".join(
        f"#{h['rank']} {h['handle']} ({h['reason']})" for h in skipped) + "."


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ranked creator shortlist for a HoReCa business.")
    parser.add_argument("--seed", help="prefill from a Cafe Profiles row (Establishment Name)")
    parser.add_argument("--city")
    parser.add_argument("--tone", help="content tone preference (Lists ContentTonePref)")
    parser.add_argument("--budget", help="Lists BudgetPreference")
    parser.add_argument("--max-budget", type=int, help="max spend per creator, Rs (used by the budget filter)")
    parser.add_argument("--budget-filter", action="store_true", help="hide creators over budget (estimated rates)")
    parser.add_argument("--name")
    parser.add_argument("--area")
    parser.add_argument("--objective")
    parser.add_argument("--format")
    parser.add_argument("--price")
    parser.add_argument("--vibe")
    parser.add_argument("--top", type=int, default=cfg.SHORTLIST_SIZE)
    args = parser.parse_args(argv)

    vocab = load_vocab()
    try:
        fields = {"city": args.city, "tone_preference": args.tone, "budget_preference": args.budget,
                  "max_budget_inr": args.max_budget, "name": args.name, "area": args.area,
                  "campaign_objective": args.objective, "preferred_format": args.format,
                  "price_bracket": args.price, "vibe": args.vibe}
        if args.seed:
            seed = seed_requirements(vocab, args.seed)
            base = {"city": seed["city"], "tone_preference": seed["tone_pref"],
                    "budget_preference": seed["budget_preference"], **seed["context"]}
            fields = {**base, **{k: v for k, v in fields.items() if v is not None}}
        fields["city"] = fields.get("city") or cfg.DEFAULT_CAFE_CITY
        req = make_requirements(vocab, **fields)
    except (ValueError, KeyError) as e:
        print(f"Invalid requirements: {e}", file=sys.stderr)
        return 2

    result = shortlist(load_pool(), req, args.budget_filter)
    if result["message"]:
        print(f"\n=== Shortlist: {req['name']} ===\n{result['message']}")
        return 0
    visible = result["rows"]

    print(f"\n=== Shortlist: {req['name']} ===")
    print(f"Scored on   : city={req['city']} (locality 50%), tone={req['tone_pref']} (content 30%), engagement 20%")
    print(f"Budget      : {req['budget_preference']}"
          + (f", max Rs {req['max_budget_inr']:,} per creator" if req["max_budget_inr"] else ""))
    print("Context (display only - NOT used in ranking or filtering):")
    for k, v in req["context"].items():
        if k != "name":
            print(f"  {k:<18} {v}")
    print(f"\n{result['filter_note']}")
    print(f"Showing {min(args.top, len(visible))} of {len(visible)} (of {result['eligible']} eligible)\n")
    print(f"{'#':>3}  {'handle':<28}{'final':>7}{'loc':>7}{'cont':>7}{'eng':>7}  {'locality':<22}{'engagement':<12}est. rate")
    for r in visible[:args.top]:
        rate = (r["rate_band"] or "-").split(" indicative")[0]
        print(f"{r['rank']:>3}  {r['handle']:<28}{r['final_score']:>7.3f}{r['locality']:>7.3f}{r['content']:>7.3f}"
              f"{r['engagement']:>7.3f}  {r['locality_tier'] + '/' + r['confidence']:<22}"
              f"{r['engagement_confidence']:<12}{rate}")
        print(f"     {r['rationale']}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    logging.getLogger("validate").setLevel(logging.ERROR)  # validation log is reviewed separately
    sys.exit(main())
