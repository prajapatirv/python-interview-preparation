"""Interaction data: attempts, saved answers and submissions. Evidence only - never the source of truth.

``Store`` documents the repository interface the API depends on. ``SqliteStore`` is the local
single-user implementation (``app/services/supabase_store.py`` is the multi-user one); ``user_id`` is a
column from day one so the move needs no schema change. Rows come back as plain dicts.

Submission lifecycle: ``pending`` (passed the automatic gate, waiting for a reviewer) -> ``approved`` ->
``promoted`` (written into the Markdown bank), or ``rejected`` (by the gate or by a reviewer).
"""
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Protocol

LOCAL_USER = "local"

ATTEMPT_FIELDS = ("question_id", "stack", "topic", "level", "answer_text", "check", "provider", "prompt_version")


class Store(Protocol):
    def add_attempt(self, *, question_id: str, stack: str, topic: str, level: str, answer_text: str,
                    check: dict, provider: str, prompt_version: str = "", user_id: str = LOCAL_USER) -> dict: ...
    def attempts(self, question_id: str, *, saved_only: bool = False, user_id: str = LOCAL_USER) -> list[dict]: ...
    def get_attempt(self, attempt_id: int, *, user_id: str | None = LOCAL_USER) -> dict | None: ...
    def save(self, attempt_id: int, label: str, *, user_id: str = LOCAL_USER) -> dict | None: ...
    def delete(self, attempt_id: int, *, user_id: str = LOCAL_USER) -> bool: ...
    def all_attempts(self, since: float = 0.0, *, user_id: str | None = None) -> list[dict]: ...
    def add_submission(self, *, attempt: dict, angle: str, status: str, gate: dict) -> dict: ...
    def submissions(self, status: str | None = None, *, user_id: str | None = None) -> list[dict]: ...
    def get_submission(self, submission_id: int) -> dict | None: ...
    def review_submission(self, submission_id: int, status: str, *, note: str = "", reviewer_id: str = "",
                         promoted_to: str = "") -> dict | None: ...


def total_score(scores: dict) -> float:
    return round(sum(scores.values()) / len(scores), 2) if scores else 0.0


SCHEMA = """
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, question_id TEXT NOT NULL,
    stack TEXT NOT NULL, topic TEXT NOT NULL DEFAULT '', level TEXT NOT NULL DEFAULT '',
    answer_text TEXT NOT NULL, check_json TEXT NOT NULL, total_score REAL NOT NULL,
    provider TEXT NOT NULL, prompt_version TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL,
    saved INTEGER NOT NULL DEFAULT 0, label TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS ix_attempts_q ON attempts(user_id, question_id, created_at);
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id INTEGER NOT NULL, user_id TEXT NOT NULL,
    question_id TEXT NOT NULL, stack TEXT NOT NULL, angle TEXT NOT NULL DEFAULT '',
    answer_text TEXT NOT NULL, status TEXT NOT NULL, gate_json TEXT NOT NULL, provider TEXT NOT NULL DEFAULT '',
    review_note TEXT NOT NULL DEFAULT '', reviewer_id TEXT NOT NULL DEFAULT '', promoted_to TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL, updated_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS ix_submissions_status ON submissions(status, created_at);
"""


class SqliteStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(SCHEMA)
            cols = {r["name"] for r in self._db.execute("PRAGMA table_info(attempts)")}
            if "prompt_version" not in cols:                 # databases created by Phase A
                self._db.execute("ALTER TABLE attempts ADD COLUMN prompt_version TEXT NOT NULL DEFAULT ''")
            self._db.commit()

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _attempt(r) -> dict:
        d = dict(r)
        d["check"] = json.loads(d.pop("check_json"))
        d["saved"] = bool(d["saved"])
        return d

    @staticmethod
    def _submission(r) -> dict:
        d = dict(r)
        d["gate"] = json.loads(d.pop("gate_json"))
        return d

    def _one(self, sql, args):
        with self._lock:
            return self._db.execute(sql, args).fetchone()

    def _all(self, sql, args=()):
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    # ------------------------------------------------------------------ attempts
    def add_attempt(self, *, question_id, stack, topic, level, answer_text, check, provider,
                    prompt_version="", user_id=LOCAL_USER) -> dict:
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO attempts (user_id, question_id, stack, topic, level, answer_text, check_json,"
                " total_score, provider, prompt_version, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (user_id, question_id, stack, topic, level, answer_text, json.dumps(check),
                 total_score(check.get("scores", {})), provider, prompt_version, time.time()))
            self._db.commit()
            row = self._db.execute("SELECT * FROM attempts WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._attempt(row)

    def attempts(self, question_id, *, saved_only=False, user_id=LOCAL_USER) -> list[dict]:
        sql = "SELECT * FROM attempts WHERE user_id=? AND question_id=?" + (" AND saved=1" if saved_only else "")
        return [self._attempt(r) for r in self._all(sql + " ORDER BY created_at DESC, id DESC", (user_id, question_id))]

    def get_attempt(self, attempt_id, *, user_id=LOCAL_USER) -> dict | None:
        if user_id is None:
            r = self._one("SELECT * FROM attempts WHERE id=?", (attempt_id,))
        else:
            r = self._one("SELECT * FROM attempts WHERE id=? AND user_id=?", (attempt_id, user_id))
        return self._attempt(r) if r else None

    def save(self, attempt_id, label, *, user_id=LOCAL_USER) -> dict | None:
        with self._lock:
            self._db.execute("UPDATE attempts SET saved=1, label=? WHERE id=? AND user_id=?",
                             (label[:80], attempt_id, user_id))
            self._db.commit()
        return self.get_attempt(attempt_id, user_id=user_id)

    def delete(self, attempt_id, *, user_id=LOCAL_USER) -> bool:
        with self._lock:
            n = self._db.execute("DELETE FROM attempts WHERE id=? AND user_id=?", (attempt_id, user_id)).rowcount
            self._db.commit()
        return n > 0

    def all_attempts(self, since=0.0, *, user_id=None) -> list[dict]:
        sql, args = "SELECT * FROM attempts WHERE created_at>=?", [since]
        if user_id is not None:
            sql, args = sql + " AND user_id=?", args + [user_id]
        return [self._attempt(r) for r in self._all(sql + " ORDER BY created_at", args)]

    # ------------------------------------------------------------------ submissions
    def add_submission(self, *, attempt, angle, status, gate) -> dict:
        now = time.time()
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO submissions (attempt_id, user_id, question_id, stack, angle, answer_text, status,"
                " gate_json, provider, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (attempt["id"], attempt["user_id"], attempt["question_id"], attempt["stack"], angle[:80],
                 attempt["answer_text"], status, json.dumps(gate), attempt["provider"], now, now))
            self._db.commit()
            row = self._db.execute("SELECT * FROM submissions WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._submission(row)

    def submissions(self, status=None, *, user_id=None) -> list[dict]:
        sql, args, where = "SELECT * FROM submissions", [], []
        if status:
            where.append("status=?"), args.append(status)
        if user_id is not None:
            where.append("user_id=?"), args.append(user_id)
        if where:
            sql += " WHERE " + " AND ".join(where)
        return [self._submission(r) for r in self._all(sql + " ORDER BY created_at DESC, id DESC", args)]

    def get_submission(self, submission_id) -> dict | None:
        r = self._one("SELECT * FROM submissions WHERE id=?", (submission_id,))
        return self._submission(r) if r else None

    def review_submission(self, submission_id, status, *, note="", reviewer_id="", promoted_to="") -> dict | None:
        with self._lock:
            self._db.execute("UPDATE submissions SET status=?, review_note=?, reviewer_id=?, promoted_to=?,"
                             " updated_at=? WHERE id=?",
                             (status, note[:500], reviewer_id, promoted_to, time.time(), submission_id))
            self._db.commit()
        return self.get_submission(submission_id)
