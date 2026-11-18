"""Choosing between the Claude API and the offline mock, and streaming a mock answer.

Credentials, in the order the ``anthropic`` SDK (1.13+) itself resolves them:

1. ``ANTHROPIC_API_KEY`` (an API key from the Claude Console);
2. ``ANTHROPIC_AUTH_TOKEN`` (a bearer token);
3. an ``ant auth login`` profile on disk (``ANTHROPIC_PROFILE`` or the active profile).

The recommended local setup is 3: run ``ant auth login`` once and no key is stored in the repo.
Usage is billed to the Claude Console organization you sign in to, like an API key.

Both apps then select a provider from ``AI_MODE`` (``auto`` | ``claude`` | ``mock``):

- ``mock`` always gives the offline mock;
- with any credential above, anything else gives Claude;
- without one, ``claude`` gives Claude only when the app passes ``keyless_claude=True``
  (the coach does); otherwise the mock, so a missing credential never breaks the page.
"""
import asyncio
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path


def config_dir() -> Path:
    """Where ``ant auth login`` stores profiles (same rule as the SDK)."""
    env = os.getenv("ANTHROPIC_CONFIG_DIR")
    if env:
        return Path(env)
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        return (Path(appdata) if appdata else Path.home() / "AppData" / "Roaming") / "Anthropic"
    return Path.home() / ".config" / "anthropic"


def login_profile() -> str | None:
    """The name of the ``ant auth login`` profile the SDK would use, or None when there is none."""
    base = config_dir()
    name = os.getenv("ANTHROPIC_PROFILE", "").strip()
    if not name:
        try:
            name = (base / "active_config").read_text(encoding="utf-8").strip()
        except OSError:
            name = ""
    name = name or "default"
    if "/" in name or "\\" in name or name.startswith("."):
        return None
    ok = (base / "configs" / f"{name}.json").is_file() and (base / "credentials" / f"{name}.json").is_file()
    return name if ok else None


def credential_source() -> str | None:
    """``'api-key'``, ``'auth-token'``, ``'login:<profile>'``, or None. An empty variable does not count."""
    if os.getenv("ANTHROPIC_API_KEY"):
        return "api-key"
    if os.getenv("ANTHROPIC_AUTH_TOKEN"):
        return "auth-token"
    profile = login_profile()
    return f"login:{profile}" if profile else None


def has_credentials() -> bool:
    return credential_source() is not None


def describe(source: str | None) -> str:
    """A short label for the UI."""
    if source is None:
        return "none (offline mock)"
    if source.startswith("login:"):
        return f"ant auth login ({source[6:]} profile)"
    return {"api-key": "API key", "auth-token": "auth token"}.get(source, source)


def pick_provider(wanted: str | None, *, keyless_claude: bool = False) -> str:
    """Returns ``'claude'`` or ``'mock'`` for the requested ``AI_MODE``."""
    wanted = (wanted or "auto").strip().lower()
    if wanted == "mock":
        return "mock"
    if has_credentials():
        return "claude"
    return "claude" if wanted == "claude" and keyless_claude else "mock"


async def stream_text(text: str, size: int = 40, delay: float = 0.01) -> AsyncIterator[str]:
    """Yields ``text`` in chunks with a short pause, so the mock streams in the UI like the real API."""
    for i in range(0, len(text), size):
        yield text[i:i + size]
        await asyncio.sleep(delay)
