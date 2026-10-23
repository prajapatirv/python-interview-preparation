"""Canaries against the real content repos (skipped if they are absent).

These are the tests that catch a question source silently dropping out of the coach — the
"nothing forgotten" guarantee. When content is added on purpose, update the numbers here.
"""
import pytest

from app import config
from app.services.library import Library

pytestmark = pytest.mark.skipif(not (config.WORKSPACE_ROOT / "java" / "java-interview-prep").is_dir(),
                                reason="real content repos not present")


@pytest.fixture(scope="module")
def lib():
    return Library.load()


def test_every_question_source_is_wired_in(lib):
    for s in lib.coverage()["stacks"]:
        assert s["unreferenced"] == [], f"{s['stack']}: question files not wired into any skill: {s['unreferenced']}"


def test_existing_banks_load_completely(lib):
    by_kind = {s["stack"]: s["by_kind"] for s in lib.coverage()["stacks"]}
    assert by_kind["java"]["crib"] == 473            # every Q in java-interview-prep/topics/*.md
    assert by_kind["java"]["guide"] >= 240           # the QA guide, round questions, docx supplement
    assert by_kind["java"]["deepdive"] >= 441          # incl. company-chase-travel/brush-up (120)
    assert by_kind["java"]["scenario"] >= 743          # all banks incl. profile pack 70-78 + company pack 80-82
    assert by_kind["python"]["deepdive"] >= 380
    assert by_kind["python"]["index"] >= 300


def test_topics_match_the_job_requirement(lib):
    java = {t.id for t in lib.stack("java").topics}
    assert {"kafka", "rest-api", "microservices", "spring-boot", "java-core", "nosql", "splunk-observability",
            "performance", "genai"} <= java


def test_scenario_answers_follow_the_format(lib):
    for q in lib.questions("java"):
        if q["kind"] != "scenario":
            continue
        keys = {s["key"] for s in q["sections"]}
        missing = {"scenario", "probe", "answer", "tradeoffs", "spoken"} - keys
        assert not missing, f"{q['source']} Q{q['num']} is missing sections {missing}"
        assert q["tags"], f"{q['source']} Q{q['num']} has no tags"


def test_question_ids_are_unique(lib):
    for s in lib.stacks:
        ids = [q["id"] for q in lib.questions(s.id)]
        assert len(ids) == len(set(ids))


def test_general_bucket_stays_small(lib):
    """If this grows, a topic's keywords need extending (skills/<stack>/NN_*.md)."""
    for s in lib.stacks:
        assert len(lib.questions(s.id, "general")) <= 10
