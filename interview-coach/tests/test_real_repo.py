"""Canaries against the real content repos (skipped if they are absent).

These are the tests that catch a question source silently dropping out of the coach — the
"nothing forgotten" guarantee. When content is added on purpose, update the numbers here.
"""
import json
import re
from pathlib import Path

import pytest

from app import config
from app.services import tracks
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
    assert by_kind["java"]["scenario"] >= 988          # all banks incl. profile pack 70-78, company packs 80-87, target companies 90-94, reported pack
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


def test_reported_pack_references_exist(lib):
    """The reported-interviews hub promises an answer per question: every "Bank N Qm" must be a real question."""
    pack = config.WORKSPACE_ROOT / "java" / "java-interview-prep"
    numbered = {}
    for q in lib.questions("java"):
        if q["kind"] == "scenario":
            bank = Path(q["source"]).name.split("_")[0]
            numbered.setdefault(bank, set()).add(q["num"])
    files = [pack / "reported-interviews" / "README.md"]
    for prefix in ("33", "66", "67", "68", "69", "88", "89", "95", "96", "97", "98", "99"):
        files += list((pack / "interview-scenarios").glob(prefix + "_*.md"))
    assert len(files) == 13
    for f in files:
        for bank, num in re.findall(r"[Bb]ank (\d+) Q(\d+)", f.read_text(encoding="utf-8")):
            assert int(num) in numbered.get(bank, ()), f"{f.name} refers to missing bank {bank} Q{num}"


def test_tracks_point_at_real_topics_and_stay_focused(lib):
    """A track must narrow the bank a lot, and the senior track must lean towards design more than the early one."""
    plans = {}
    for stack in ("java", "python"):
        ids = {t.id for t in lib.stack(stack).topics}
        for track in tracks.load(stack)["tracks"]:
            assert {f["topic"] for f in track["focus"]} <= ids, f"{stack}/{track['id']} names an unknown topic"
        for summary in tracks.summaries(stack):
            plan = tracks.plan(lib, stack, summary["id"])
            assert all(t["questions"] for t in plan["topics"]), f"{stack}/{summary['id']} has an empty topic"
            assert 60 <= plan["total"] <= 320, f"{stack}/{summary['id']} has {plan['total']} questions"
            chosen = [q["id"] for t in plan["topics"] for q in t["questions"]]
            assert len(chosen) == len(set(chosen))
            plans[stack, summary["id"]] = plan
    early, senior, architect = plans["java", "early"], plans["java", "senior"], plans["java", "architect"]
    assert senior["stages"]["senior"] > senior["stages"]["architect"]        # hands-on: depth leads
    assert architect["stages"]["architect"] > architect["stages"]["senior"]  # architect: design leads
    assert architect["stages"]["architect"] > senior["stages"]["architect"]
    assert "architect" not in early["stages"]
    assert early["stages"]["fresher"] > early["stages"].get("senior", 0)


def test_topic_tags_move_a_question_to_its_card(lib):
    coins = next(q for q in lib.questions("java") if q["title"].startswith("Find the least number of coins"))
    assert coins["topic"] == "coding"
    assert coins["id"] in {q["id"] for q in lib.topic("java", "coding").questions}
    assert coins["id"] not in {q["id"] for q in lib.topic("java", "spring-boot").questions}


def test_plans_for_other_people_hold_no_personal_material(lib):
    for summary in tracks.summaries("java"):
        for t in tracks.plan(lib, "java", summary["id"])["topics"]:
            for q in t["questions"]:
                full = lib.question(q["id"])
                assert not re.search(r"8[012]_company_chase|40_leadership|19-resume", full["source"]), full["title"]
                assert "hackathon" not in full["title"] and "Why Nagarro" not in full["title"]


def test_general_bucket_stays_small(lib):
    """If this grows, a topic's keywords need extending (skills/<stack>/NN_*.md)."""
    for s in lib.stacks:
        assert len(lib.questions(s.id, "general")) <= 10


def test_answer_map_reviewed_ids_exist(lib):
    """Retitling a question changes its id; the page build needs the reviewed list to follow."""
    reviewed = Path(__file__).resolve().parents[1] / "scripts" / "answer_map" / "reviewed"
    ids = [i for batch in reviewed.glob("batch*.json") for i in json.loads(batch.read_text())]
    assert ids
    known = {q["id"] for t in lib.stack("java").topics for q in lib.questions("java", t.id)}
    assert [i for i in ids if i not in known] == []
