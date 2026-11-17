import asyncio

import pytest

from prepkit import env, llm


@pytest.fixture(autouse=True)
def no_credentials(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)


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


def test_stream_text_rejoins_to_the_original():
    async def collect():
        return [c async for c in llm.stream_text("abcdefghij", size=4, delay=0)]
    assert asyncio.run(collect()) == ["abcd", "efgh", "ij"]
