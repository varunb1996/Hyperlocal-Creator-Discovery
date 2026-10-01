"""History list (GET /shortlists). Uses an empty in-memory DB, so it needs no creator data and runs on CI."""
import pytest
from fastapi.testclient import TestClient

import api
from tests.fake_supabase import FakeSupabase


@pytest.fixture
def client():
    store = FakeSupabase().client()
    api.app.dependency_overrides = {api.get_db: lambda: store}
    yield TestClient(api.app)
    api.app.dependency_overrides = {}


def test_history_lists_saved_shortlists_newest_first(client):
    assert client.get("/shortlists").json() == []
    first = client.post("/shortlist", json={"tone_preference": "Fun/Energetic", "name": "First Cafe", "area": "Baner"}).json()
    second = client.post("/shortlist", json={"city": "Mumbai", "tone_preference": "Desi/Relatable", "name": "Second"}).json()
    client.post("/shortlist", json={"tone_preference": "Fun/Energetic", "save": False})  # re-rank only: not listed

    history = client.get("/shortlists").json()
    assert [h["shortlist_id"] for h in history] == [second["shortlist_id"], first["shortlist_id"]]
    assert history[1] | {"created_at": None} == {
        "shortlist_id": first["shortlist_id"], "created_at": None, "supported": True, "name": "First Cafe",
        "area": "Baner", "city": "Pune", "tone_preference": "Fun/Energetic", "budget_preference": "Not Yet Decided"}
    assert history[0]["supported"] is False  # out-of-scope city is listed, marked unsupported


def test_history_limit(client):
    for i in range(3):
        client.post("/shortlist", json={"tone_preference": "Fun/Energetic", "name": f"Cafe {i}"})
    assert len(client.get("/shortlists?limit=2").json()) == 2
    assert client.get("/shortlists?limit=0").status_code == 422


def test_root_redirects_to_docs(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/docs"
