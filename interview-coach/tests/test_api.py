"""API behaviour in offline mock mode (no network, no key)."""
import json


def test_status_and_stacks(client):
    st = client.get("/api/status").json()
    assert st["ai"]["provider"] == "mock"
    stacks = client.get("/api/stacks").json()
    assert stacks[0]["id"] == "java"
    assert {t["id"] for t in stacks[0]["topics"]} == {"kafka", "java-core", "general"}


def test_topic_detail(client):
    t = client.get("/api/topics/java/kafka").json()
    assert t["examples"]["files"] == ["01_demo.java"]
    assert {d["path"] for d in t["docs"]} == {"java/prep/deep_dive/12_kafka.md", "java/prep/topics/09-kafka.md"}
    assert client.get("/api/topics/java/nope").status_code == 404


def test_search_ranks_the_scenario_first(client):
    hits = client.get("/api/search/java", params={"q": "How can we do rebalancing in Kafka?"}).json()
    assert hits[0]["title"] == "How do you handle consumer-group rebalancing in production?"


def test_ask_streams_grounded_answer(client):
    r = client.post("/api/ai", json={"mode": "ask", "stack": "java", "text": "kafka rebalancing in production"})
    assert r.status_code == 200
    refs = json.loads(r.headers["x-ai-refs"])
    assert refs[0]["kind"] == "scenario"
    assert "Closest answer in your bank" in r.text


def test_interview_mode_returns_a_scores_line(client):
    qid = next(q["id"] for q in client.get("/api/topics/java/kafka").json()["questions"] if q["num"] == 1
               and q["kind"] == "scenario")
    r = client.post("/api/ai", json={"mode": "interview", "stack": "java", "question_id": qid,
                                     "answer": "In production we had 400k lag during deploys, so we used static "
                                               "membership and monitored rebalancing; the trade-off is slower failover."})
    assert "### Scorecard" in r.text
    assert r.text.strip().splitlines()[-1].startswith("SCORES: scenario=")
    assert "Why not raise max.poll.interval.ms?" in r.text           # follow-up comes from the bank


def test_bad_requests(client):
    assert client.post("/api/ai", json={"mode": "nope", "stack": "java"}).status_code == 400
    assert client.post("/api/ai", json={"mode": "explain", "stack": "java"}).status_code == 400
    assert client.post("/api/ai", json={"mode": "ask", "stack": "cobol"}).status_code == 400
    assert client.get("/api/doc", params={"path": "../../etc/passwd"}).status_code == 404


def test_round_prefers_scenarios(client):
    qs = client.get("/api/round/java", params={"topics": "kafka", "n": 2}).json()
    assert [q["kind"] for q in qs] == ["scenario", "scenario"]


def test_save_validates_format(client):
    bad = client.post("/api/questions/save", json={"stack": "java", "topic": "kafka", "markdown": "just text"})
    assert bad.status_code == 422
    md = "### Q0 [mid] What is a partition?\ntags: partitions\n\n**The live scenario**\nX.\n\n**60-second answer**\nY.\n"
    ok = client.post("/api/questions/save", json={"stack": "java", "topic": "kafka", "markdown": md})
    assert ok.status_code == 200
    titles = [q["title"] for q in client.get("/api/topics/java/kafka").json()["questions"]]
    assert "What is a partition?" in titles                          # visible right after the reload


def test_jd_mode_ranks_topics(client):
    r = client.post("/api/ai", json={"mode": "jd", "stack": "java",
                                     "text": "Strong Kafka: partitions, consumer groups, rebalancing. Java equals/hashCode."})
    tops = json.loads(r.headers["x-ai-topics"])
    assert tops[0]["id"] == "kafka"
