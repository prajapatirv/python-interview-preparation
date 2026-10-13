"""Phase B: both Store implementations satisfy one contract. The Supabase store runs against a small fake of
PostgREST (filters ``eq.``/``gte.``, ``order``, ``Prefer: return=representation``), so request shapes are
checked without a live project."""
import json

import httpx
import pytest

from app.services.store import SqliteStore
from app.services.supabase_store import SupabaseError, SupabaseStore


class FakePostgrest:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {"attempts": [], "submissions": []}
        self.seq = 0
        self.requests: list[httpx.Request] = []

    def _match(self, row, params):
        for k, v in params.items():
            if k in ("order", "select"):
                continue
            op, _, val = v.partition(".")
            cell = row[k]
            if op == "eq":
                ok = str(cell).lower() == val.lower() if isinstance(cell, bool) else str(cell) == val
            elif op == "gte":
                ok = cell >= float(val)
            else:
                raise AssertionError(f"unsupported operator {op}")
            if not ok:
                return False
        return True

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert request.headers["apikey"] and request.headers["authorization"].startswith("Bearer ")
        table = request.url.path.rsplit("/", 1)[-1]
        rows = self.tables[table]
        params = dict(request.url.params)
        if request.method == "POST":
            self.seq += 1
            row = {"id": self.seq, "saved": False, "label": "", "review_note": "", "reviewer_id": "",
                   "promoted_to": "", **json.loads(request.content)}
            rows.append(row)
            return httpx.Response(201, json=[row])
        hits = [r for r in rows if self._match(r, params)]
        if request.method == "GET":
            for key in reversed(params.get("order", "").split(",")):
                if key:
                    col, _, direction = key.partition(".")
                    hits.sort(key=lambda r: r[col], reverse=direction == "desc")
            return httpx.Response(200, json=hits)
        if request.method == "PATCH":
            for r in hits:
                r.update(json.loads(request.content))
            return httpx.Response(200, json=hits)
        if request.method == "DELETE":
            for r in hits:
                rows.remove(r)
            return httpx.Response(200, json=hits)
        raise AssertionError(request.method)


@pytest.fixture(params=["sqlite", "supabase"])
def store(request, tmp_path):
    if request.param == "sqlite":
        return SqliteStore(tmp_path / "t.db")
    fake = FakePostgrest()
    client = httpx.Client(base_url="https://x.supabase.co/rest/v1", transport=httpx.MockTransport(fake),
                          headers={"apikey": "k", "Authorization": "Bearer k"})
    s = SupabaseStore("https://x.supabase.co", "k", client=client)
    s.fake = fake
    return s


CHECK = {"claims": [{"text": "a", "verdict": "incorrect", "correction": "b", "source": "knowledge"}],
         "scores": {"scenario": 4, "depth": 4, "tradeoffs": 2, "monitoring": 2, "clarity": 3}}


def _add(store, user="u1", qid="q1", **kw):
    return store.add_attempt(question_id=qid, stack="java", topic="kafka", level="senior", answer_text="my answer",
                             check=CHECK, provider="claude", prompt_version="abc12345", user_id=user, **kw)


def test_attempt_roundtrip_and_ordering(store):
    a1, a2 = _add(store), _add(store)
    assert a1["check"] == CHECK and a1["total_score"] == 3.0 and a1["saved"] is False
    assert [a["id"] for a in store.attempts("q1", user_id="u1")] == [a2["id"], a1["id"]]   # newest first
    assert store.attempts("q1", user_id="someone-else") == []


def test_save_delete_are_scoped_to_the_owner(store):
    a = _add(store)
    assert store.save(a["id"], "label", user_id="intruder") is None
    assert store.delete(a["id"], user_id="intruder") is False
    s = store.save(a["id"], "Spring angle", user_id="u1")
    assert s["saved"] is True and s["label"] == "Spring angle"
    assert [x["id"] for x in store.attempts("q1", saved_only=True, user_id="u1")] == [a["id"]]
    assert store.delete(a["id"], user_id="u1") is True
    assert store.get_attempt(a["id"], user_id="u1") is None


def test_all_attempts_since_and_user_filter(store):
    _add(store, user="u1"), _add(store, user="u2", qid="q2")
    assert len(store.all_attempts()) == 2
    assert len(store.all_attempts(user_id="u2")) == 1
    assert store.all_attempts(since=9e12) == []


def test_submission_lifecycle(store):
    a = _add(store)
    s = store.add_submission(attempt=a, angle="Spring angle", status="pending", gate={"passed": True, "reasons": []})
    assert s["status"] == "pending" and s["gate"]["passed"] and s["question_id"] == "q1"
    assert [x["id"] for x in store.submissions("pending")] == [s["id"]]
    assert store.submissions("pending", user_id="u2") == []
    done = store.review_submission(s["id"], "promoted", note="ok", reviewer_id="boss", promoted_to="x.md")
    assert (done["status"], done["review_note"], done["promoted_to"]) == ("promoted", "ok", "x.md")
    assert store.submissions("pending") == []
    assert store.get_submission(9999) is None


def test_supabase_surfaces_http_errors():
    client = httpx.Client(base_url="https://x/rest/v1",
                          transport=httpx.MockTransport(lambda r: httpx.Response(401, text="bad key")))
    with pytest.raises(SupabaseError, match="401"):
        SupabaseStore("https://x", "k", client=client).attempts("q1")


def test_migration_copies_attempts_and_repoints_submissions(tmp_path):
    import importlib.util
    import sys
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "migrate", Path(__file__).resolve().parent.parent / "scripts" / "migrate_sqlite_to_supabase.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["migrate"] = mod
    spec.loader.exec_module(mod)

    src = SqliteStore(tmp_path / "src.db")
    a = src.add_attempt(question_id="q1", stack="java", topic="kafka", level="senior", answer_text="x",
                        check=CHECK, provider="claude", prompt_version="v")
    src.save(a["id"], "keep")
    src.add_submission(attempt=src.get_attempt(a["id"]), angle="ang", status="pending", gate={"passed": True})
    dst = SqliteStore(tmp_path / "dst.db")
    assert mod.migrate(src, dst, "supabase-user-1") == (1, 1)
    moved = dst.all_attempts()[0]
    assert moved["user_id"] == "supabase-user-1" and moved["saved"] and moved["label"] == "keep"
    assert dst.submissions()[0]["user_id"] == "supabase-user-1"
