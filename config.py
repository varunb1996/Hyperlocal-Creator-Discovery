"""Scoring config — the product levers. Translated from Matching_Engine.xlsx 'Config' tab."""

# Final score weights (must sum to 100). Config!B5:B7
WEIGHTS = {"locality": 50, "content": 30, "engagement": 20}

# Locality. Config!B11:B13
PROXY_CAP = 0.6               # max locality a proxy (inferred) match can earn; verified scores sit above it
PROXY_POINTS_BASE_CITY = 1    # creator base location contains the cafe city
PROXY_POINTS_FEATURES_CITY = 1  # creator regularly features cafe-city venues
FEATURES_CREDIT = {"Yes": 1.0, "Occasionally": 0.5, "No": 0.0}  # share of the features-point earned
FEATURES_COLUMN_CITY = "Pune"   # the "Regularly Features Pune Venues?" column only speaks for Pune
DEFAULT_CAFE_CITY = "Pune"      # Cafe Profiles has no city column; every cafe is in Pune

# Engagement sub-weights (must sum to 1). Config!B17:B18
ENGAGEMENT_WEIGHTS = {"er": 0.6, "pace": 0.4}

# ER is scaled against this percentile of the pool (not the max), then capped at 1.
# Real outliers keep their value and score 1.0; they just stop flattening everyone else.
ER_CEILING_PERCENTILE = 95

# ER validation (validate.py). Stored ER% should equal engagements / followers.
ER_REVIEW_TOLERANCE = 0.25           # relative gap beyond which two ER values "disagree"
ARBITER_LC_PER_PLAY = (0.002, 0.20)  # (likes+comments)/plays band for the arbiter to be trusted
ER_IMPLAUSIBLE = 1.0                 # no arbiter: stored ER above 100% ...
ER_INFLATION_FACTOR = 10             # ... or above 10x engagements/followers is a clear outlier

# Posting pace score map. Config!A22:B26
PACE_SCORES = {
    "High (every 1-3 days)": 1.0,
    "Moderate (every 4-7 days)": 0.8,
    "Low (every 8-14 days)": 0.4,
    "Inactive (15+ days)": 0.1,
    "Insufficient Data": 0.0,
}

# Content match: CONTENT_MATCH[creator tone][cafe tone preference] -> 0..1. Config!A30:G36
_TONES = ["Fun/Energetic", "Aesthetic/Calm", "Witty/Comedic",
          "Informative/Reviewer", "Luxury/Aspirational", "Desi/Relatable"]
_MATRIX = [
    [1.0, 0.3, 0.6, 0.3, 0.3, 0.6],
    [0.3, 1.0, 0.3, 0.4, 0.6, 0.3],
    [0.6, 0.3, 1.0, 0.4, 0.3, 0.3],
    [0.3, 0.4, 0.4, 1.0, 0.3, 0.3],
    [0.3, 0.6, 0.3, 0.3, 1.0, 0.3],
    [0.6, 0.3, 0.3, 0.3, 0.3, 1.0],
]
CONTENT_MATCH = {row: dict(zip(_TONES, vals)) for row, vals in zip(_TONES, _MATRIX)}

# Number of top-ranked creators returned per brief (API default; overridable per request with top_n).
SHORTLIST_SIZE = 5

# Pilot scope: creator pool is Pune-area only. Other cities are accepted but get a not-supported message, no list.
PILOT_CITY = "Pune"

# Authenticity dampener: engagement sub-score x multiplier, by the enrichment's "Engagement Authenticity Read".
# Modest on purpose: the read is an estimate, not proof. Unknown/absent values -> 1.0 (absence is not penalized).
AUTHENTICITY_MULTIPLIER = {
    "Looks Genuine": 1.0,
    "Some Red Flags": 0.85,
    "Likely Inflated": 0.7,
    "Not Assessed": 1.0,
}

# Tie-breaker: final scores within TIE_EPSILON (0-1 scale; 0.001 = 0.1 points) count as tied and are ordered by
# location tier (this order: measured beats inferred), then location fit, then engagement, then handle A-Z.
TIE_EPSILON = 0.001
TIE_TIER_ORDER = ["Verified", "Proxy", "Unknown"]

# Eligibility
EXCLUDED_CATEGORIES = {"Other"}  # venue/business (and off-domain) accounts, not creators
REQUIRED_FIELDS = ["Username", "ER%", "content_tone", "Posting Pace Category"]

# Rationale wording thresholds. Scorer!K
CONTENT_BANDS = [(0.8, "strongly"), (0.5, "partially"), (0.0, "weakly")]
ENGAGEMENT_BANDS = [(0.7, "high"), (0.4, "moderate"), (0.0, "low")]

if sum(WEIGHTS.values()) != 100:
    raise ValueError(f"WEIGHTS must sum to 100, got {sum(WEIGHTS.values())}")
if abs(sum(ENGAGEMENT_WEIGHTS.values()) - 1) > 1e-9:
    raise ValueError("ENGAGEMENT_WEIGHTS must sum to 1")
