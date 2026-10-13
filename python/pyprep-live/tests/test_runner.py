import time

from app import config

from .conftest import events


def test_run_streams_start_lines_end(client):
    ev = events(client.post("/api/run", json={"id": "01_demo/01_alpha.py"}))
    assert ev[0]["type"] == "start" and ev[0]["python"] == config.PYTHON_VERSION
    assert [e["line"] for e in ev if e["type"] == "out"] == ["hello", "world"]
    assert ev[-1]["type"] == "end" and ev[-1]["reason"] == "ok" and ev[-1]["code"] == 0


def test_stderr_and_exit_code_reported(client):
    ev = events(client.post("/api/run", json={"id": "01_demo/03_fails.py"}))
    assert any(e["type"] == "err" and e["line"] == "boom" for e in ev)
    assert ev[-1]["reason"] == "error" and ev[-1]["code"] == 3


def test_pytest_suite_runs(client):
    ev = events(client.post("/api/run", json={"id": "02_checks/::pytest"}))
    assert ev[-1]["reason"] == "ok"
    assert any("PASSED" in e.get("line", "") for e in ev)


def test_timeout_fires_even_when_output_never_goes_idle(client, allow_edit, monkeypatch):
    # Regression: the timeout used to be checked only when the queue was idle for 0.25s,
    # so a script that prints constantly never timed out.
    monkeypatch.setattr(config, "RUN_TIMEOUT_S", 1)
    code = "import time\nwhile True:\n    print('x')\n    time.sleep(0.01)\n"
    start = time.perf_counter()
    ev = events(client.post("/api/run", json={"id": "01_demo/01_alpha.py", "code": code}))
    assert ev[-1]["reason"] == "timeout"
    assert time.perf_counter() - start < 10


def test_output_cap_truncates_runaway_prints(client, allow_edit, monkeypatch):
    monkeypatch.setattr(config, "MAX_OUTPUT_BYTES", 2000)
    code = "while True:\n    print('y' * 100)\n"
    ev = events(client.post("/api/run", json={"id": "01_demo/01_alpha.py", "code": code}))
    assert ev[-1]["reason"] == "truncated"


def test_edited_code_runs_and_leaves_no_temp_file(client, allow_edit, fake_repo):
    ev = events(client.post("/api/run", json={"id": "01_demo/01_alpha.py", "code": "print('edited')"}))
    assert any(e.get("line") == "edited" for e in ev)
    assert list((fake_repo / "01_demo").glob("_live_*.py")) == [fake_repo / "01_demo" / "_live_leftover.py"]
