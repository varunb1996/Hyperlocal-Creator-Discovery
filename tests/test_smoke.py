"""Deploy smoke test: the API boots and serves from committed files only (no workbook, no Supabase)."""
from fastapi.testclient import TestClient

import api


def test_health():
    assert TestClient(api.app).get("/health").json() == {"status": "ok"}


def test_vocab_served_from_committed_json():
    body = TestClient(api.app).get("/vocab").json()
    assert "Aesthetic/Calm" in body["tone_preference"] and "Paid Only" in body["budget_preference"]
