"""Integration checks against the real ../python-interview-prep folder (skipped if absent)."""
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import create_app
from app.services import catalog, docs

from .conftest import events

pytestmark = pytest.mark.skipif(not config.PREP_ROOT.exists(), reason="PREP_ROOT not found")


@pytest.fixture(scope="module")
def real():
    return TestClient(create_app())


def test_all_topics_and_key_examples(real):
    cat = real.get("/api/catalog").json()
    # Every numbered folder on disk must reach the catalog: a mismatch means discovery dropped one.
    # Counted independently of catalog.TOPIC_RE, so a regex change cannot hide a lost folder.
    on_disk = sorted(p.name for p in config.PREP_ROOT.iterdir()
                     if p.is_dir() and p.name[:2].isdigit() and p.name[2] == "_")
    assert [t["id"] for t in cat["topics"]] == on_disk
    assert len(on_disk) >= 14                     # floor: the folders never shrink
    ids = {e["id"] for t in cat["topics"] for e in t["examples"]}
    assert {"01_python_core/03_decorators.py", "04_testing_tdd/::pytest", "11_coding_challenges/::pytest"} <= ids


def test_deep_dive_readme_contract():
    """Every deep_dive/NN_*.md has a table row that docs.ROW_RE parses, and every link in it resolves.

    This is the check that catches a reformatted README table: the rows stop matching and every
    example silently loses its deep-dive link, while the app keeps working."""
    deep = config.PREP_ROOT / "deep_dive"
    readme = (deep / "README.md").read_text(encoding="utf-8")
    rows = [m for line in readme.splitlines() if (m := docs.ROW_RE.match(line))]
    documents = sorted(p.name for p in deep.glob("[0-9][0-9]_*.md"))
    assert sorted(m.group(2) for m in rows) == documents, "a deep dive has no parseable row in deep_dive/README.md"
    for m in rows:
        targets = docs.TARGET_RE.findall(m.group(3))
        assert targets, f"row {m.group(1)} links no runnable companion"
        for topic, name in targets:
            assert (config.PREP_ROOT / topic / name).exists(), f"row {m.group(1)} links missing ../{topic}/{name}"


def test_every_example_has_an_outline():
    """Files with no '# ----' banner or section() call show an empty outline in the UI."""
    bare = []
    for folder in sorted(config.PREP_ROOT.glob("[0-9][0-9]_*")):
        for py in sorted(folder.glob("[0-9][0-9]_*.py")):
            if not catalog.analyse_source(py.read_text(encoding="utf-8"))["sections"]:
                bare.append(f"{folder.name}/{py.name}")
    assert bare == [], f"no section banners: {bare}"


def test_sections_infra_and_deep_dive_links(real):
    ex = {e["id"]: e for t in real.get("/api/catalog").json()["topics"] for e in t["examples"]}
    assert len(ex["01_python_core/04_generators_iterators.py"]["sections"]) >= 4
    assert ex["06_kafka/01_producer_basics.py"]["infra"]
    assert ex["01_python_core/03_decorators.py"]["docs"]


def test_pandas_example_finds_relative_csv(real):
    ev = events(real.post("/api/run", json={"id": "03_pandas_data_handling/01_series_dataframe_basics.py"}))
    assert ev[-1]["reason"] == "ok"


def test_repo_pytest_suite_runs(real):
    ev = events(real.post("/api/run", json={"id": "04_testing_tdd/::pytest"}))
    assert ev[-1]["reason"] == "ok" and any("passed" in e.get("line", "") for e in ev)


def test_java_twins_come_from_the_shared_pairs_table(real):
    """shared/cross-stack-pairs.md links paired programs to the Java runner (the 100 -> 600 TPS scenario is in both)."""
    cat = real.get("/api/catalog").json()
    ex = {e["id"]: e for t in cat["topics"] for e in t["examples"]}
    twins = ex["13_system_design_scenarios/03_capacity_scaling_tps.py"]["twins"]
    assert {"topic": "Capacity: 100 to 600 TPS with Little's Law",
            "id": "16_system_design/01_capacity_littles_law_100_to_600_tps.java"} in twins
    assert ex["04_testing_tdd/::pytest"]["twins"]                       # a folder link pairs the suite
    assert cat["features"]["twin_url"].startswith("http://127.0.0.1:")
