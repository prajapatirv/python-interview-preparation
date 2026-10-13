from app.services.library import Library

from conftest import write


def test_every_source_is_loaded_and_assigned(workspace):
    lib = Library.load()
    kafka = lib.topic("java", "kafka")
    kinds = sorted({q["kind"] for q in kafka.questions})
    assert kinds == ["crib", "deepdive", "guide", "scenario"]
    assert kafka.scenario_files == ["java/prep/interview-scenarios/02_kafka_consumers.md"]
    # guide questions are classified by keywords; the enum question has none, so it lands in general
    guide = {q["title"]: q["topic"] for q in lib.questions("java") if q["kind"] == "guide"}
    assert guide["How do you scale Kafka consumers?"] == "kafka"
    assert guide["What is the difference between `==` and `equals()`?"] == "java-core"
    assert guide["What is an enum"] == "general"
    # a "Fresher questions" section sets the level; unlabelled deep-dive questions default to mid
    assert next(q for q in lib.questions("java") if q["title"] == "What is an enum")["level"] == "fresher"
    assert {q["level"] for q in kafka.questions if q["kind"] == "deepdive"} == {"mid"}


def test_question_ids_are_unique(workspace):
    lib = Library.load()
    ids = [q["id"] for q in lib.questions("java")]
    assert len(ids) == len(set(ids))


def test_coverage_flags_an_unwired_question_file(workspace):
    assert Library.load().coverage()["stacks"][0]["unreferenced"] == []
    write(workspace / "java/prep/New_QA.md", "## Q1. A brand new question?\nAnswer.\n")
    report = Library.load().coverage()["stacks"][0]
    assert report["unreferenced"] == [{"path": "java/prep/New_QA.md", "questions": 1}]


def test_docs_are_whitelisted(workspace):
    lib = Library.load()
    assert lib.allowed_doc("java/prep/deep_dive/12_kafka.md") is not None
    assert lib.allowed_doc("java/prep/Guide.md") is not None
    assert lib.allowed_doc("../outside.md") is None
    assert lib.allowed_doc("skills/java/_persona.md") is None


def test_save_question_appends_with_next_number(workspace):
    lib = Library.load()
    path = lib.save_question("java", "kafka", "architect", "How do you size partitions?",
                             "**The live scenario**\nX.\n\n**60-second answer**\nY.", ["partitions", "ai-draft"])
    assert path == "java/prep/interview-scenarios/02_kafka_consumers.md"
    q = next(q for q in Library.load().questions("java", "kafka") if q["title"] == "How do you size partitions?")
    assert (q["num"], q["level"], q["kind"]) == (3, "architect", "scenario")


def test_save_question_creates_a_bank_for_a_topic_without_one(workspace):
    path = Library.load().save_question("java", "java-core", "mid", "Why is String immutable?",
                                        "**The live scenario**\nX.", [])
    assert path.startswith("java/prep/interview-scenarios/")
    assert any(q["kind"] == "scenario" for q in Library.load().questions("java", "java-core"))
