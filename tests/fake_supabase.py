"""In-memory stand-in for the Supabase REST API (PostgREST), served through httpx.MockTransport.

Exercises db.Supabase's real HTTP/JSON path without a live project. Supports only what db.py uses.
"""
import json
import uuid
from datetime import datetime, timezone

import httpx

import db


class FakeSupabase:
    def __init__(self):
        self.tables = {"creators": [], "cafe_briefs": [], "shortlists": []}
        self.requests = []

    def handler(self, request):
        self.requests.append(request)
        table = request.url.path.rsplit("/", 1)[-1]
        rows = self.tables[table]
        if request.method == "GET":
            params = request.url.params
            out = rows
            for key, value in params.items():
                if value.startswith("eq."):
                    out = [r for r in out if str(r.get(key)) == value[3:]]
                elif value.startswith("in.("):
                    wanted = set(value[4:-1].split(","))
                    out = [r for r in out if str(r.get(key)) in wanted]
            if order := params.get("order"):
                col, direction = order.split(".")
                out = sorted(out, key=lambda r: r[col], reverse=direction == "desc")
            if limit := params.get("limit"):
                out = out[: int(limit)]
            if (select := params.get("select", "*")) != "*":
                out = [{c: r.get(c) for c in select.split(",")} for r in out]
            return httpx.Response(200, json=out)
        if request.method == "POST":
            new = json.loads(request.content)
            upsert_on = request.url.params.get("on_conflict")
            for row in new:
                row.setdefault("id", str(uuid.uuid4()))
                row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                if upsert_on:
                    rows[:] = [r for r in rows if r[upsert_on] != row[upsert_on]]
                rows.append(row)
            return httpx.Response(201, json=new)
        return httpx.Response(405)

    def client(self):
        return db.Supabase("https://fake.supabase.co", "test-key", transport=httpx.MockTransport(self.handler))
