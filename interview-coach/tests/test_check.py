"""Check my answer: structured fact-check, stored attempts, saved answers (offline mock provider)."""
import pytest

from app.services import checker

ANSWER = ("In production we had 400k lag during deploys. We used static membership so a restart does not "
          "trigger a rebalance. The trade-off is slower failover. I would watch consumer lag per partition.")


def _qid(client):
    return next(q["id"] for q in client.get("/api/topics/java/kafka").json()["questions"]
                if q["num"] == 1 and q["kind"] == "scenario")


def test_check_returns_structured_result_and_stores_attempt(client):
    qid = _qid(client)
    r = client.post("/api/check", json={"stack": "java", "question_id": qid, "answer": ANSWER})
    assert r.status_code == 200
    a = r.json()
    c = a["check"]
    assert c["provider"] == "mock" and c["claims"]
    assert {x["verdict"] for x in c["claims"]} <= set(checker.VERDICTS)
    assert set(c["scores"]) == set(checker.DIM_KEYS)
    assert "incorrect" not in {x["verdict"] for x in c["claims"]}     # the mock never invents a wrong verdict
    assert a["total_score"] == round(sum(c["scores"].values()) / 5, 2)
    assert [x["id"] for x in client.get("/api/attempts", params={"question_id": qid}).json()] == [a["id"]]


def test_save_label_and_delete(client):
    qid = _qid(client)
    a = client.post("/api/check", json={"stack": "java", "question_id": qid, "answer": ANSWER}).json()
    s = client.post(f"/api/attempts/{a['id']}/save", json={"label": "Spring Kafka angle"}).json()
    assert s["saved"] and s["label"] == "Spring Kafka angle"
    only = client.get("/api/attempts", params={"question_id": qid, "saved_only": True}).json()
    assert len(only) == 1
    assert client.delete(f"/api/attempts/{a['id']}").status_code == 200
    assert client.delete(f"/api/attempts/{a['id']}").status_code == 404
    assert client.post("/api/attempts/999/save", json={"label": "x"}).status_code == 404


def test_free_question_and_validation(client):
    ok = client.post("/api/check", json={"stack": "java", "text": "What is a partition?", "answer": ANSWER})
    assert ok.status_code == 200
    assert client.post("/api/check", json={"stack": "java", "answer": ANSWER}).status_code == 400     # no question
    assert client.post("/api/check", json={"stack": "cobol", "text": "x", "answer": ANSWER}).status_code == 400
    assert client.post("/api/check", json={"stack": "java", "text": "x", "answer": "  "}).status_code == 422


def test_normalise_coerces_untrusted_model_output():
    raw = {"claims": [{"text": "a", "verdict": "maybe", "source": "made-up-id"}, {"text": ""}, "junk"],
           "scores": {"scenario": 9, "depth": "3", "tradeoffs": None}, "missing": ["x", ""]}
    out = checker.normalise(raw, {"real-id"})
    assert out["claims"] == [{"text": "a", "verdict": "unverifiable", "correction": "", "source": "knowledge"}]
    assert out["scores"] == {"scenario": 5, "depth": 3, "tradeoffs": 1, "monitoring": 1, "clarity": 1}
    assert out["missing"] == ["x"]


@pytest.mark.parametrize("text", ['```json\n{"a": 1}\n```', 'Here you go: {"a": 1} hope it helps'])
def test_parse_json_tolerates_fences_and_preamble(text):
    assert checker.parse_json(text) == {"a": 1}
