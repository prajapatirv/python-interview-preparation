from app.services import docs
from app.services.catalog import Catalog


def examples(client):
    cat = client.get("/api/catalog").json()
    return cat, {e["id"]: e for t in cat["topics"] for e in t["examples"]}


def test_topics_and_examples_discovered(client):
    cat, ex = examples(client)
    assert [t["id"] for t in cat["topics"]] == ["01_demo", "02_checks"]
    assert "01_demo/01_alpha.py" in ex
    assert ex["01_demo/01_alpha.py"]["description"] == "Alpha demo: prints two lines."


def test_banner_sections_and_experiments(client):
    _, ex = examples(client)
    alpha = ex["01_demo/01_alpha.py"]
    assert [s["title"] for s in alpha["sections"]] == ["part one", "part two"]
    assert [e["text"] for e in alpha["experiments"]] == ["change the greeting"]


def test_section_call_fallback_when_no_banners(client):
    _, ex = examples(client)
    assert [s["title"] for s in ex["01_demo/02_beta.py"]["sections"]] == ["first", "second"]


def test_runner_temp_files_and_conftest_are_hidden(client):
    _, ex = examples(client)
    assert not any("_live_" in i for i in ex)


def test_suite_card_created_for_tests_dir_only(client):
    _, ex = examples(client)
    assert ex["02_checks/::pytest"]["kind"] == "suite"
    assert "01_demo/::pytest" not in ex


def test_deep_dive_links_by_file_and_by_folder(client):
    _, ex = examples(client)
    assert [d["id"] for d in ex["01_demo/01_alpha.py"]["docs"]] == ["01_demo_doc"]
    assert ex["01_demo/02_beta.py"]["docs"] == []
    assert [d["id"] for d in ex["02_checks/01_helper.py"]["docs"]] == ["02_checks_doc"]
    assert [d["id"] for d in ex["02_checks/::pytest"]["docs"]] == ["02_checks_doc"]


def test_reload_picks_up_new_files(fake_repo):
    cat = Catalog()
    before = len(cat.index)
    (fake_repo / "01_demo" / "09_new.py").write_text("print(1)\n", encoding="utf-8")
    assert cat.reload() == before + 1


def test_missing_root_reports_error(monkeypatch, tmp_path):
    from app import config
    monkeypatch.setattr(config, "PREP_ROOT", tmp_path / "nope")
    assert "PREP_ROOT not found" in Catalog().error


def test_docs_are_served_but_traversal_is_not(client):
    ok = client.get("/api/docs/01_demo_doc")
    assert ok.status_code == 200 and "Demo doc" in ok.json()["markdown"]
    assert client.get("/api/docs/README").status_code == 200          # lives in deep_dive/, allowed
    assert client.get("/api/docs/nope").status_code == 404
    assert client.get("/api/docs/..%2FCLAUDE").status_code == 404


def test_read_doc_rejects_paths_outside_deep_dive(fake_repo):
    (fake_repo / "secret.md").write_text("secret", encoding="utf-8")
    assert docs.read_doc(fake_repo, "../secret") is None
