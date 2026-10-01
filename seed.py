"""One-time seeding: workbook -> Phase 1 normalize -> Phase 3 ER validation -> Supabase `creators`.

Only whitelisted columns (db.CREATOR_FIELDS) are sent; email/phone/address never leave this machine.
Also exports the Lists vocabulary to data/vocab.json so the API never needs the workbook at runtime.
"""
import json
import logging
import os
from pathlib import Path

import db
from normalize import load_creators, load_mappings, load_vocab, normalize
from validate import validate_er

VOCAB_JSON = os.getenv("VOCAB_JSON", str(Path(__file__).parent / "data" / "vocab.json"))
PII_COLUMNS = ("Email Address", "Phone Number", "Address")

log = logging.getLogger(__name__)


def build_rows(raw_creators=None):
    """Cleaned, validated creators as DB rows (PII-free by construction)."""
    vocab = load_vocab()
    raw = load_creators() if raw_creators is None else raw_creators
    creators, _ = validate_er(normalize(raw, load_mappings(vocab)))
    return [db.to_db_row(c) for c in creators]


def write_vocab(path=VOCAB_JSON):
    Path(path).write_text(json.dumps({k: sorted(v) for k, v in sorted(load_vocab().items())}, indent=2),
                          encoding="utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("validate").setLevel(logging.WARNING)
    write_vocab()
    rows = build_rows()
    db.from_env().insert("creators", rows, upsert_on="handle")
    log.info("Upserted %d creators (columns: %s). Wrote %s.", len(rows), ", ".join(rows[0]), VOCAB_JSON)
