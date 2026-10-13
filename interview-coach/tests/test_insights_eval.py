"""Phase E: the improvement dashboard numbers and the checker eval harness."""
import asyncio
import json

import pytest

from app import config
from app.services import evaluation, insights

DAY = 86400
NOW = 1_800_000_000.0


def _attempt(qid, score, age_days, claims=(), topic="kafka", provider="claude"):
    return {"question_id": qid, "topic": topic, "total_score": score, "created_at": NOW - age_days * DAY,
            "provider": provider, "check": {"claims": [{"text": t, "verdict": v, "correction": "fix " + t,
                                                         "source": "knowledge"} for t, v in claims]}}


def test_insights_aggregates_scores_trend_and_misconceptions():
    rows = [_attempt("q1", 2.0, 20, [("auto commit is safe", "incorrect"), ("lag exists", "correct")]),
            _attempt("q1", 3.0, 10, [("Auto commit is safe", "incorrect")]),
            _attempt("q1", 4.0, 1, [("lag exists", "correct")]),
            _attempt("q2", 5.0, 2, topic="java-core")]
    subs = [{"status": "promoted", "reviewer_id": "me"}, {"status": "rejected", "reviewer_id": "me"},
            {"status": "pending", "reviewer_id": ""}, {"status": "rejected", "reviewer_id": ""}]
    out = insights.build(rows, subs, {"q1": "Kafka Q"}, now=NOW)
    kafka = next(t for t in out["by_topic"] if t["topic"] == "kafka")
    assert kafka["attempts"] == 3 and kafka["avg_score"] == 3.0
    assert kafka["trend"] == 1.5                       # last week 4.0 vs earlier avg 2.5
    assert kafka["wrong_claim_rate"] == 0.5            # 2 wrong of 4 claims
    assert out["by_topic"][0]["topic"] == "kafka"      # weakest topic first
    assert out["weakest_questions"][0] == {"question_id": "q1", "title": "Kafka Q", "attempts": 3,
                                           "avg_score": 3.0, "wrong_claim_rate": 0.5}
    m = out["misconceptions"][0]
    assert (m["claim"], m["count"], m["title"]) == ("auto commit is safe", 2, "Kafka Q") and m["correction"]
    assert out["submissions"]["acceptance_rate"] == 0.5      # only human-reviewed ones count
    assert out["submissions"]["by_status"]["rejected"] == 2


def test_insights_handles_no_data():
    out = insights.build([], [])
    assert out["attempts"] == 0 and out["avg_score"] is None and out["by_topic"] == []


CASE = {"id": "c1", "question_title": "What is a consumer group?", "answer": "x",
        "planted": [{"contains": "one consumer", "truth": "right"}, {"contains": "share partitions", "truth": "wrong"},
                    {"contains": "never mentioned", "truth": "wrong"}]}


def _check(claims):
    return {"claims": [{"text": t, "verdict": v} for t, v in claims]}


def test_score_case_and_summary_numbers():
    rows = evaluation.score_case(CASE, _check([("each partition goes to one consumer", "correct"),
                                              ("extras share partitions", "incorrect")]))
    assert [(r["found"], r["ok"]) for r in rows] == [(True, True), (True, True), (False, False)]
    s = evaluation.summarise(rows, "claude", "v1", "m")
    assert s["coverage"] == round(2 / 3, 3)
    assert s["error_recall"] == 0.5 and s["false_alarm_rate"] == 0.0
    assert [f["contains"] for f in s["failures"]] == ["never mentioned"]


def test_false_alarm_and_missed_error_are_counted():
    rows = evaluation.score_case(CASE, _check([("one consumer only", "incorrect"), ("they share partitions", "correct")]))
    s = evaluation.summarise(rows, "claude", "v1", "m")
    assert s["false_alarm_rate"] == 1.0 and s["error_recall"] == 0.0
    assert not evaluation.passes(s)


def test_gate_thresholds_and_mock_is_never_evaluable():
    good = {"evaluable": True, "error_recall": 0.8, "false_alarm_rate": 0.1}
    assert evaluation.passes(good)
    assert not evaluation.passes({**good, "error_recall": 0.7})
    assert not evaluation.passes({**good, "false_alarm_rate": 0.3})
    assert not evaluation.passes({**good, "evaluable": False})
    assert evaluation.summarise([], "mock", "mock", "offline mock")["evaluable"] is False


def test_run_skips_unknown_questions_and_flags_mock(workspace):
    from app.services.library import Library
    lib = Library.load()
    cases = [{"id": "ok", "question_title": "What is a consumer group?", "answer": "Each partition goes to one member "
              "of the group at a time.", "planted": [{"contains": "one member", "truth": "right"}]},
             {"id": "gone", "question_title": "Not in the bank", "answer": "x", "planted": []}]
    out = asyncio.run(evaluation.run(lib, "java", cases))
    assert out["skipped_cases"] == ["gone"] and out["provider"] == "mock" and out["evaluable"] is False
    assert out["claims"] == 1


def test_record_and_history_roundtrip(workspace):
    evaluation.record({"prompt_version": "a", "passed": False})
    evaluation.record({"prompt_version": "b", "passed": True})
    assert [r["prompt_version"] for r in evaluation.history()] == ["a", "b"]


def test_eval_endpoints(client):
    r = client.post("/api/evals/run")
    assert r.status_code == 200
    assert r.json()["evaluable"] is False and r.json()["passed"] is False      # mock provider: honest "no"
    assert len(client.get("/api/evals").json()) == 1


def test_insights_endpoint_after_a_check(client):
    qid = next(q["id"] for q in client.get("/api/topics/java/kafka").json()["questions"] if q["num"] == 1)
    for _ in range(2):
        client.post("/api/check", json={"stack": "java", "question_id": qid,
                                        "answer": "Each partition goes to one consumer in the group at a time."})
    d = client.get("/api/insights").json()
    assert d["attempts"] == 2 and d["by_topic"][0]["topic"] == "kafka" and d["weakest_questions"][0]["attempts"] == 2


def test_case_file_is_well_formed():
    cases = evaluation.load_cases()
    assert len({c["id"] for c in cases}) == len(cases)
    for c in cases:
        assert c["question_title"] and c["answer"]
        for p in c["planted"]:
            assert p["truth"] in ("right", "wrong")
            assert p["contains"].lower() in c["answer"].lower(), f"{c['id']}: '{p['contains']}' not in the answer"
    assert any(p["truth"] == "wrong" for c in cases for p in c["planted"])


@pytest.mark.skipif(not (config.WORKSPACE_ROOT / "java" / "java-interview-prep").is_dir(),
                    reason="real content repos not present")
def test_every_eval_case_resolves_to_a_real_bank_question():
    from app.services.library import Library
    titles = {q["title"] for q in Library.load().questions("java")}
    missing = [c["id"] for c in evaluation.load_cases() if c["question_title"] not in titles]
    assert missing == [], f"eval cases whose question title is not in the bank: {missing}"
