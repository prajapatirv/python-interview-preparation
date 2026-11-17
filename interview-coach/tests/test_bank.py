from app.services import bank

from conftest import CRIB, DEEP, GUIDE, SCENARIO


def test_scenario_questions_sections_and_tags():
    meta, intro, qs = bank.parse_questions(SCENARIO.lstrip())
    assert meta["skill"] == "kafka"
    assert intro == "Intro text."
    assert [q["num"] for q in qs] == [1, 2]
    q = qs[0]
    assert q["level"] == "senior"
    assert q["tags"] == ["rebalancing", "static-membership"]
    assert [s["key"] for s in q["sections"]] == ["scenario", "answer", "followups", "spoken"]
    assert "# not a heading" in bank.section(q, "answer")          # fenced '#' lines are not headings
    assert bank.followups(q) == ["Why not raise max.poll.interval.ms?"]


def test_crib_levels_map_onto_experience_bands():
    _, _, qs = bank.parse_questions(CRIB.lstrip())
    assert [q["level"] for q in qs] == ["fresher", "architect"]
    assert qs[0]["body"] == "A distributed log."


def test_deep_dive_question_ends_at_next_section_heading():
    _, _, qs = bank.parse_questions(DEEP.lstrip())
    assert [q["title"] for q in qs] == ["What is lag?", "Why rebalance?"]
    assert qs[1]["level"] is None
    assert "worked example" not in qs[1]["body"]


def test_guide_questions_keep_their_parent_section():
    _, _, qs = bank.parse_questions(GUIDE.lstrip())
    assert [(q["label"], q["section"]) for q in qs] == [
        ("Q1", "1. Core Java Fundamentals"), ("Q2", "8. Apache Kafka"), ("B1", "B. Fresher questions")]


def test_index_bullets():
    text = """### 01 — Python Core

**`01_data_structures.py`**

- **Q:** Why choose a tuple over a list,
  and when can it NOT be a key?
  **A:** Tuples are immutable.
  -> [link](x.py#L1)
- **Q:** Second question?
  **A:** Second answer.
"""
    qs = bank.parse_index(text)
    assert [q["title"] for q in qs] == ["Why choose a tuple over a list, and when can it NOT be a key?", "Second question?"]
    assert qs[0]["section"] == "01 — Python Core"
    assert qs[0]["body"].startswith("Tuples are immutable.")


def test_stable_id_is_deterministic():
    assert bank.stable_id("a", "b") == bank.stable_id("a", "b") != bank.stable_id("a", "c")


def test_pinned_qid_is_read_in_either_order_and_kept_out_of_the_body():
    text = ("### Q1 [senior] First?\nqid: kafka-lag-spike\ntags: kafka, lag\n\n**The live scenario**\nx\n\n"
            "### Q2 [mid] Second?\ntags: a\n\nbody\n\n"
            "### Q3 [mid] Third?\nqid: Not Valid!\n\nbody\n")
    q1, q2, q3 = bank.parse_questions(text)[2]
    assert q1["qid"] == "kafka-lag-spike" and q1["tags"] == ["kafka", "lag"] and "qid" not in q1["body"]
    assert "qid" not in q2
    assert "qid" not in q3 and q3["body"].startswith("qid: Not Valid!")   # malformed: left as text, not an id
