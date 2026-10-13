"""Multi-user ``Store`` on Supabase (Postgres via PostgREST). Same interface as ``SqliteStore``.

Uses plain ``httpx`` against ``<SUPABASE_URL>/rest/v1`` with the **service-role key**, so it runs on the
server only and *bypasses* Row Level Security: every query here filters on ``user_id`` itself. The RLS
policies in ``supabase/schema.sql`` protect the same tables if a browser ever talks to Supabase directly.

Timestamps are epoch seconds (double precision) so rows are identical to the SQLite ones and
``scripts/migrate_sqlite_to_supabase.py`` can copy them unchanged.

NOT exercised against a live project in this repo's tests (needs credentials): ``tests/test_supabase_store.py``
checks the request shapes against a fake transport.
"""
import time

import httpx

from .store import LOCAL_USER, total_score


class SupabaseError(RuntimeError):
    pass


class SupabaseStore:
    def __init__(self, url: str, service_key: str, *, client: httpx.Client | None = None):
        self._client = client or httpx.Client(
            base_url=url.rstrip("/") + "/rest/v1", timeout=15,
            headers={"apikey": service_key, "Authorization": f"Bearer {service_key}",
                     "Content-Type": "application/json"})

    # ------------------------------------------------------------------ plumbing
    def _call(self, method: str, table: str, *, params=None, json=None, returning=True) -> list[dict]:
        headers = {"Prefer": "return=representation"} if returning else {}
        r = self._client.request(method, "/" + table, params=params, json=json, headers=headers)
        if r.status_code >= 400:
            raise SupabaseError(f"{method} {table}: {r.status_code} {r.text[:300]}")
        return r.json() if returning and r.content else []

    @staticmethod
    def _attempt(d: dict) -> dict:
        d = dict(d)
        d["check"] = d.pop("check_json")
        return d

    @staticmethod
    def _submission(d: dict) -> dict:
        d = dict(d)
        d["gate"] = d.pop("gate_json")
        return d

    # ------------------------------------------------------------------ attempts
    def add_attempt(self, *, question_id, stack, topic, level, answer_text, check, provider,
                    prompt_version="", user_id=LOCAL_USER) -> dict:
        row = {"user_id": user_id, "question_id": question_id, "stack": stack, "topic": topic, "level": level,
               "answer_text": answer_text, "check_json": check, "total_score": total_score(check.get("scores", {})),
               "provider": provider, "prompt_version": prompt_version, "created_at": time.time()}
        return self._attempt(self._call("POST", "attempts", json=row)[0])

    def attempts(self, question_id, *, saved_only=False, user_id=LOCAL_USER) -> list[dict]:
        params = {"user_id": f"eq.{user_id}", "question_id": f"eq.{question_id}",
                  "order": "created_at.desc,id.desc"}
        if saved_only:
            params["saved"] = "eq.true"
        return [self._attempt(d) for d in self._call("GET", "attempts", params=params)]

    def get_attempt(self, attempt_id, *, user_id=LOCAL_USER) -> dict | None:
        params = {"id": f"eq.{attempt_id}"}
        if user_id is not None:
            params["user_id"] = f"eq.{user_id}"
        rows = self._call("GET", "attempts", params=params)
        return self._attempt(rows[0]) if rows else None

    def save(self, attempt_id, label, *, user_id=LOCAL_USER) -> dict | None:
        rows = self._call("PATCH", "attempts", params={"id": f"eq.{attempt_id}", "user_id": f"eq.{user_id}"},
                          json={"saved": True, "label": label[:80]})
        return self._attempt(rows[0]) if rows else None

    def delete(self, attempt_id, *, user_id=LOCAL_USER) -> bool:
        return bool(self._call("DELETE", "attempts", params={"id": f"eq.{attempt_id}", "user_id": f"eq.{user_id}"}))

    def all_attempts(self, since=0.0, *, user_id=None) -> list[dict]:
        params = {"created_at": f"gte.{since}", "order": "created_at.asc"}
        if user_id is not None:
            params["user_id"] = f"eq.{user_id}"
        return [self._attempt(d) for d in self._call("GET", "attempts", params=params)]

    # ------------------------------------------------------------------ submissions
    def add_submission(self, *, attempt, angle, status, gate) -> dict:
        now = time.time()
        row = {"attempt_id": attempt["id"], "user_id": attempt["user_id"], "question_id": attempt["question_id"],
               "stack": attempt["stack"], "angle": angle[:80], "answer_text": attempt["answer_text"],
               "status": status, "gate_json": gate, "provider": attempt["provider"],
               "created_at": now, "updated_at": now}
        return self._submission(self._call("POST", "submissions", json=row)[0])

    def submissions(self, status=None, *, user_id=None) -> list[dict]:
        params = {"order": "created_at.desc,id.desc"}
        if status:
            params["status"] = f"eq.{status}"
        if user_id is not None:
            params["user_id"] = f"eq.{user_id}"
        return [self._submission(d) for d in self._call("GET", "submissions", params=params)]

    def get_submission(self, submission_id) -> dict | None:
        rows = self._call("GET", "submissions", params={"id": f"eq.{submission_id}"})
        return self._submission(rows[0]) if rows else None

    def review_submission(self, submission_id, status, *, note="", reviewer_id="", promoted_to="") -> dict | None:
        rows = self._call("PATCH", "submissions", params={"id": f"eq.{submission_id}"},
                          json={"status": status, "review_note": note[:500], "reviewer_id": reviewer_id,
                                "promoted_to": promoted_to, "updated_at": time.time()})
        return self._submission(rows[0]) if rows else None
