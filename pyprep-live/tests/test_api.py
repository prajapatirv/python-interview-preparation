from app import config
from .conftest import events


def test_catalog_reports_features(client):
    f = client.get("/api/catalog").json()["features"]
    assert f["python"] == config.PYTHON_VERSION and f["edit"] is False and "timeout" in f


def test_unknown_example_is_404(client):
    assert client.post("/api/run", json={"id": "nope"}).status_code == 404
    assert client.get("/api/source", params={"id": "nope"}).status_code == 404
    assert client.post("/api/ai", json={"id": "nope"}).status_code == 404


def test_source_endpoint(client):
    assert "hello" in client.get("/api/source", params={"id": "01_demo/01_alpha.py"}).json()["source"]
    assert client.get("/api/source", params={"id": "02_checks/::pytest"}).json()["source"] == ""


def test_edit_forbidden_by_default(client):
    r = client.post("/api/run", json={"id": "01_demo/01_alpha.py", "code": "print(1)"})
    assert r.status_code == 403


def test_edit_of_a_suite_is_rejected(client, allow_edit):
    r = client.post("/api/run", json={"id": "02_checks/::pytest", "code": "print(1)"})
    assert r.status_code == 400


def test_ai_falls_back_to_mock_without_key(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AI_MODE", raising=False)
    assert client.get("/api/catalog").json()["features"]["ai_mode"] == "mock"
    r = client.post("/api/ai", json={"id": "01_demo/01_alpha.py", "mode": "explain"})
    text = "".join(e.get("text", "") for e in events(r))     # chunks can split a phrase
    assert "mock mode" in text and "part one" in text


def test_ai_mode_selection(monkeypatch):
    from app.services import ai
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AI_MODE", "auto")
    assert ai.mode() == "claude"
    monkeypatch.setenv("AI_MODE", "mock")          # forced mock even with a key
    assert ai.mode() == "mock"
    monkeypatch.setenv("AI_MODE", "claude")
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert ai.mode() == "mock"                      # claude requested but no key: never fail


def test_mock_answers_cover_every_mode():
    from app.services.ai import MODES, mock_answer
    src = "# ------ Part A\nvalue = 1\n# EXPERIMENT: change value\n"
    for m in MODES:
        assert "mock mode" in mock_answer(m, src, "line1\nTraceback boom", "what is value?")
    assert "change value" in mock_answer("break", src, "")
    assert "line 2: value = 1" in mock_answer("ask", src, "", "what is value")


def test_ai_rejects_unknown_mode(client):
    assert client.post("/api/ai", json={"id": "01_demo/01_alpha.py", "mode": "hack"}).status_code == 422


def test_ai_prompt_includes_source_and_log_tail():
    from app.services.ai import build_prompt
    p = build_prompt("explain", "SRC", "x" * 7000 + "TAIL", "why?")
    assert "SRC" in p and "x" * 5996 + "TAIL" in p and "x" * 5997 + "TAIL" not in p
    assert "<question>why?</question>" in p


def test_reload_endpoint(client, fake_repo):
    (fake_repo / "01_demo" / "09_new.py").write_text("print(1)\n", encoding="utf-8")
    n = client.post("/api/reload").json()["examples"]
    assert client.get("/api/source", params={"id": "01_demo/09_new.py"}).status_code == 200 and n >= 5


def test_index_page_served(client):
    assert "Python Interview Lab" in client.get("/").text
