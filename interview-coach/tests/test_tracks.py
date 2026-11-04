"""Experience tracks: the plan respects a track's topics and quotas, skips repeats and honours the viewer's changes."""
import json
import re

from fastapi.testclient import TestClient

from app import config
from app.main import create_app
from app.services import tracks
from app.services.library import Library


def _write_track(focus, quota, kinds=("scenario", "crib")):
    path = config.SKILLS_DIR / "java" / "_tracks.json"
    path.write_text(json.dumps({
        "levels_reliable": True, "kinds": list(kinds), "weights": {"core": 1.0, "also": 0.5, "aware": 0.1},
        "tracks": [{"id": "t", "label": "6+ years", "range": "5-9", "title": "T", "expect": "E", "advice": "A",
                    "quota": quota, "focus": focus}]}), encoding="utf-8")


def test_plan_uses_only_the_tracks_topics_and_quota(workspace):
    _write_track([{"topic": "kafka", "weight": "core", "why": "because"}], {"senior": 1, "fresher": 0})
    plan = tracks.plan(Library.load(), "java", "t")
    assert [t["id"] for t in plan["topics"]] == ["kafka"]
    assert plan["topics"][0]["why"] == "because"
    assert {q["level"] for q in plan["topics"][0]["questions"]} == {"senior"}
    assert plan["total"] == 1


def test_viewer_can_remove_and_add_topics(workspace):
    _write_track([{"topic": "kafka", "weight": "core", "why": "w"}], {"mid": 5, "senior": 5, "fresher": 5})
    lib = Library.load()
    assert tracks.plan(lib, "java", "t", removed={"kafka"})["topics"] == []
    other = next(t.id for t in lib.stack("java").topics if t.id != "kafka" and t.questions and t.id != "general")
    assert other in {t["id"] for t in tracks.plan(lib, "java", "t")["other_topics"]}
    added = tracks.plan(lib, "java", "t", added={other})
    assert {t["id"] for t in added["topics"]} == {"kafka", other}


def test_near_duplicate_titles_are_detected():
    def seen(title):
        return [(tracks._words(title), tracks._head(title))]
    assert tracks._repeats("Explain the consumer group", seen("What is a consumer group?"))
    assert tracks._repeats("What is a consumer group, and why can't I add more?", seen("What is a consumer group, and what happens if I run more?"))
    assert tracks._repeats("Design a notification service (email/SMS/push).", seen("Design a notification service for push, email and SMS with retries and rate limiting"))
    assert not tracks._repeats("How do you tune a Kafka producer for high throughput?", seen("How do you tune Kafka consumers for high throughput?"))
    assert not tracks._repeats("How do you tune producer batching?", seen("What is a consumer group?"))
    assert tracks._repeats("Design a URL shortener.", seen("Design a URL shortener like Bitly, with click analytics"))
    assert tracks._repeats("How does HashMap work internally (Java 8+)?", seen("How does HashMap work internally, and what happens on a collision?"))


def test_sources_take_turns_so_one_list_cannot_fill_a_stage():
    pool = [{"source": "a"}, {"source": "a"}, {"source": "a"}, {"source": "b"}]
    assert [q["source"] for q in tracks._take_turns(pool)] == ["a", "b", "a", "a"]


def test_reported_questions_are_recognised():
    assert tracks.is_reported({"tags": ["deloitte"], "source": "x.md"})
    assert tracks.is_reported({"tags": [], "source": "java/62_round_kafka.md"})
    assert not tracks.is_reported({"tags": ["reported-genai"], "source": "x.md"})


def test_exclude_keeps_personal_material_out_of_plans(workspace):
    _write_track([{"topic": "kafka", "weight": "core", "why": "w"}], {"mid": 9, "senior": 9, "fresher": 9})
    lib = Library.load()
    title = lib.topic("java", "kafka").questions[0]["title"]
    path = config.SKILLS_DIR / "java" / "_tracks.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["exclude"] = [re.escape(title)]
    path.write_text(json.dumps(data), encoding="utf-8")
    chosen = [lib.question(q["id"])["title"] for t in tracks.plan(lib, "java", "t")["topics"] for q in t["questions"]]
    assert title not in chosen


def test_track_routes(workspace):
    _write_track([{"topic": "kafka", "weight": "core", "why": "w"}], {"senior": 1})
    with TestClient(create_app()) as client:
        assert client.get("/api/tracks/java").json()[0]["id"] == "t"
        assert client.get("/api/tracks/java/t").json()["total"] == 1
        assert client.get("/api/tracks/java/t?remove=kafka").json()["total"] == 0
        assert client.get("/api/tracks/java/nope").status_code == 404
