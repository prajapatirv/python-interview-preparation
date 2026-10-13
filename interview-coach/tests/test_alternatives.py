"""Phase C: approved alternative answers - parser, gate, review queue, promotion into the Markdown bank."""
import pytest

from app import config
from app.services import auth, bank

GOOD = ("We moved to static membership with a stable group.instance.id per pod, so a rolling restart no longer "
        "triggers a rebalance. The trade-off is slower failover, because the broker waits for session.timeout.ms "
        "before reassigning, so we tuned it to 45 seconds and watched consumer lag per partition on a dashboard.")


def _qid(client):
    return next(q["id"] for q in client.get("/api/topics/java/kafka").json()["questions"]
                if q["num"] == 1 and q["kind"] == "scenario")


def _saved_attempt(client, qid, answer=GOOD, label="Spring Kafka angle"):
    a = client.post("/api/check", json={"stack": "java", "question_id": qid, "answer": answer}).json()
    client.post(f"/api/attempts/{a['id']}/save", json={"label": label})
    return a["id"]


@pytest.fixture
def lenient_gate(monkeypatch):
    # the offline mock scores heuristically; real gating needs the Claude provider
    for name, v in (("GATE_MIN_DEPTH", 1), ("GATE_MIN_TRADEOFFS", 1), ("GATE_MIN_WORDS", 10)):
        monkeypatch.setattr(config, name, v)


def test_insert_into_question_and_parse_alternatives():
    text = ("### Q1 [mid] First?\ntags: a\n\n**The live scenario**\nX.\n\n---\n\n"
            "### Q2 [mid] Second?\n\n**The live scenario**\nY.\n")
    out = bank.insert_into_question(text, "Q1", "First?", bank.render_alternative("Spring angle", "My answer."))
    _, _, qs = bank.parse_questions(out)
    assert bank.alternatives(qs[0]) == [{"angle": "Spring angle", "md": "My answer."}]
    assert qs[1]["title"] == "Second?" and bank.alternatives(qs[1]) == []     # next question untouched
    assert "---\n\n### Q2" in out                                            # rule and spacing preserved
    with pytest.raises(ValueError):
        bank.insert_into_question(text, "Q9", "Nope", "x")


def test_short_answer_is_rejected_by_the_gate(client):
    qid = _qid(client)
    aid = _saved_attempt(client, qid, answer="It uses static membership and I would monitor lag closely.")
    s = client.post(f"/api/attempts/{aid}/submit", json={}).json()
    assert s["status"] == "rejected"
    assert any("words" in r for r in s["gate"]["reasons"])
    assert client.get("/api/review").json() == []                            # never reaches the queue


def test_submit_requires_saved_answer_and_is_not_repeatable(client, lenient_gate):
    qid = _qid(client)
    a = client.post("/api/check", json={"stack": "java", "question_id": qid, "answer": GOOD}).json()
    assert client.post(f"/api/attempts/{a['id']}/submit", json={}).status_code == 400    # not saved yet
    client.post(f"/api/attempts/{a['id']}/save", json={"label": "x"})
    assert client.post(f"/api/attempts/{a['id']}/submit", json={}).json()["status"] == "pending"
    assert client.post(f"/api/attempts/{a['id']}/submit", json={}).status_code == 409


def test_approve_writes_alternative_into_the_bank_file(client, workspace, lenient_gate):
    qid = _qid(client)
    aid = _saved_attempt(client, qid)
    sub = client.post(f"/api/attempts/{aid}/submit", json={"angle": "Spring Kafka angle"}).json()
    assert sub["status"] == "pending"
    queue = client.get("/api/review").json()
    assert [s["id"] for s in queue] == [sub["id"]] and queue[0]["question_title"].startswith("How do you handle")

    done = client.post(f"/api/review/{sub['id']}", json={"decision": "approve"}).json()
    assert done["status"] == "promoted" and done["promoted_to"].endswith("02_kafka_consumers.md")
    assert "**Another strong answer (Spring Kafka angle)**" in (workspace / done["promoted_to"]).read_text("utf-8")

    q = client.get(f"/api/question/{qid}").json()                            # visible right after the reload
    assert bank.alternatives(q) == [{"angle": "Spring Kafka angle", "md": GOOD}]
    assert [s["title"] for s in client.get("/api/topics/java/kafka").json()["questions"]][:2]   # bank still loads
    assert client.post(f"/api/review/{sub['id']}", json={"decision": "approve"}).status_code == 409


def test_reject_does_not_touch_the_bank(client, workspace, lenient_gate):
    aid = _saved_attempt(client, _qid(client))
    sub = client.post(f"/api/attempts/{aid}/submit", json={}).json()
    r = client.post(f"/api/review/{sub['id']}", json={"decision": "reject", "note": "too generic"}).json()
    assert r["status"] == "rejected" and r["review_note"] == "too generic"
    assert "Another strong answer" not in (workspace / "java/prep/interview-scenarios/02_kafka_consumers.md").read_text("utf-8")


def test_learners_are_isolated_and_cannot_review(client, lenient_gate):
    app = client.app
    qid = _qid(client)
    aid = _saved_attempt(client, qid)                                       # as the local reviewer-user
    client.post(f"/api/attempts/{aid}/submit", json={})
    app.dependency_overrides[auth.current_user] = lambda: auth.User("learner-2", "learner")
    try:
        assert client.get("/api/attempts", params={"question_id": qid}).json() == []
        assert client.post(f"/api/attempts/{aid}/submit", json={}).status_code == 404
        assert client.get("/api/review").status_code == 403
        assert client.post("/api/review/1", json={"decision": "approve"}).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_supabase_mode_requires_a_token(client, monkeypatch):
    monkeypatch.setattr(config, "SUPABASE_URL", "https://example.supabase.co")
    assert client.get("/api/attempts", params={"question_id": "x"}).status_code == 401
    assert client.get("/api/attempts", params={"question_id": "x"},
                      headers={"Authorization": "Basic abc"}).status_code == 401
