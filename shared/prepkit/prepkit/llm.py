"""Choosing between the Claude API and the offline mock, and streaming a mock answer.

Both apps select a provider from ``AI_MODE`` (``auto`` | ``claude`` | ``mock``):

- ``mock`` always gives the offline mock;
- with credentials (``ANTHROPIC_API_KEY`` or ``ANTHROPIC_AUTH_TOKEN``) anything else gives Claude;
- without them, ``claude`` gives Claude only when the app passes ``keyless_claude=True``
  (the coach does, so an ``ant auth login`` profile works); otherwise the mock, so a missing key
  never breaks the page.
"""
import asyncio
import os
from collections.abc import AsyncIterator


def has_credentials() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


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
