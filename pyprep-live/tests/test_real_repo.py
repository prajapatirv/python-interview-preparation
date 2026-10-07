"""Integration checks against the real ../python-interview-prep folder (skipped if absent)."""
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import create_app

from .conftest import events

pytestmark = pytest.mark.skipif(not config.PREP_ROOT.exists(), reason="PREP_ROOT not found")


@pytest.fixture(scope="module")
def real():
    return TestClient(create_app())


def test_all_topics_and_key_examples(real):
    cat = real.get("/api/catalog").json()
    # Exact count on purpose: a drop means the catalog stopped discovering a topic folder.
    # Bump it when a numbered folder is added to ../python-interview-prep.
    assert len(cat["topics"]) == 14
    ids = {e["id"] for t in cat["topics"] for e in t["examples"]}
    assert {"01_python_core/03_decorators.py", "04_testing_tdd/::pytest", "11_coding_challenges/::pytest"} <= ids


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
