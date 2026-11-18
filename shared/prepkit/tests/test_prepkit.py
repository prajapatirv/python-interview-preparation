import asyncio

import pytest

from prepkit import env, llm


@pytest.fixture(autouse=True)
def no_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_PROFILE", raising=False)
    monkeypatch.setenv("ANTHROPIC_CONFIG_DIR", str(tmp_path / "anthropic"))   # never the real profile on this machine


def _login(tmp_path, name="default", active=None):
    base = tmp_path / "anthropic"
    for sub in ("configs", "credentials"):
        (base / sub).mkdir(parents=True, exist_ok=True)
        (base / sub / f"{name}.json").write_text("{}", encoding="utf-8")
    if active:
        (base / "active_config").write_text(active + "\n", encoding="utf-8")


def test_dotenv_real_environment_wins_and_empty_values_are_ignored(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text('# comment\nPK_A="quoted"\nPK_B=from-file\nPK_EMPTY=""\nnot a pair\n', encoding="utf-8")
    monkeypatch.setenv("PK_B", "from-env")
    monkeypatch.delenv("PK_A", raising=False)
    monkeypatch.delenv("PK_EMPTY", raising=False)
    env.load_dotenv(f)
    assert env.os.environ["PK_A"] == "quoted"
    assert env.os.environ["PK_B"] == "from-env"
    assert "PK_EMPTY" not in env.os.environ
    env.load_dotenv(tmp_path / "missing.env")          # a missing file is not an error


@pytest.mark.parametrize("wanted,keyless,expected", [
    ("auto", False, "mock"), ("", False, "mock"), (None, False, "mock"),
    ("claude", False, "mock"),                          # pyprep-live: never fail without a key
    ("claude", True, "claude"),                         # interview-coach: an `ant auth login` profile works
    ("mock", True, "mock"), ("unknown", True, "mock"),
])
def test_provider_without_credentials(wanted, keyless, expected):
    assert llm.pick_provider(wanted, keyless_claude=keyless) == expected


@pytest.mark.parametrize("var", ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"])
def test_provider_with_credentials(monkeypatch, var):
    monkeypatch.setenv(var, "x")
    assert llm.pick_provider("auto") == llm.pick_provider(" Claude ") == "claude"
    assert llm.pick_provider("mock") == "mock"         # forced mock even with a key


def test_ant_login_profile_counts_as_credentials(tmp_path):
    assert llm.credential_source() is None
    _login(tmp_path)
    assert llm.credential_source() == "login:default"
    assert llm.pick_provider("auto") == "claude"
    assert llm.describe(llm.credential_source()) == "ant auth login (default profile)"


def test_active_and_named_profiles(tmp_path, monkeypatch):
    _login(tmp_path, "work", active="work")
    assert llm.login_profile() == "work"
    monkeypatch.setenv("ANTHROPIC_PROFILE", "missing")
    assert llm.login_profile() is None                  # a named profile that does not exist is not used
    monkeypatch.setenv("ANTHROPIC_PROFILE", "../escape")
    assert llm.login_profile() is None


def test_api_key_wins_over_a_login_like_the_sdk(tmp_path, monkeypatch):
    _login(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert llm.credential_source() == "api-key"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")         # empty does not count (the .env loader never sets one)
    assert llm.credential_source() == "login:default"


def test_stream_text_rejoins_to_the_original():
    async def collect():
        return [c async for c in llm.stream_text("abcdefghij", size=4, delay=0)]
    assert asyncio.run(collect()) == ["abcd", "efgh", "ij"]


def test_pairs_table_parses_ids_for_both_runners():
    from prepkit import pairs
    text = ("| Topic | Java | Python |\n|---|---|---|\n"
            "| Locks | [a.java](../java/java-interview-prep/examples/04_c/01_a.java) | "
            "[b.py](../python/python-interview-prep/02_c/01_b.py) · [t](../python/python-interview-prep/04_t/) |\n"
            "| Other | [c.java](../java/java-interview-prep/examples/09_x/01_c.java) | "
            "[b.py](../python/python-interview-prep/02_c/01_b.py) |\n"
            "Prose | not | a row\n")
    rows = pairs.parse(text)
    assert [r["topic"] for r in rows] == ["Locks", "Other"]
    assert rows[0]["java"] == ["04_c/01_a.java"]
    assert rows[0]["python"] == ["02_c/01_b.py", "04_t/::pytest"]
    assert pairs.twins_of(rows, "python", "02_c/01_b.py") == [
        {"topic": "Locks", "id": "04_c/01_a.java"}, {"topic": "Other", "id": "09_x/01_c.java"}]
    assert pairs.twins_of(rows, "java", "04_c/01_a.java")[1]["id"] == "04_t/::pytest"
    assert pairs.twins_of(rows, "java", "nope.java") == []
