"""Settings, read from the environment. Services read `config.X` at call time so tests can monkeypatch."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent            # interview-coach/


def _load_dotenv(path: Path) -> None:
    """Minimal .env support (KEY=value lines); real environment variables win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")

WORKSPACE_ROOT = Path(os.getenv("COACH_ROOT", BASE_DIR.parent)).resolve()   # holds java/ and python/
SKILLS_DIR = Path(os.getenv("COACH_SKILLS", BASE_DIR / "skills")).resolve()
STATIC_DIR = BASE_DIR / "static"

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8100"))

# AI: AI_MODE=auto uses Claude when credentials exist, otherwise the offline mock.
AI_MODE = os.getenv("AI_MODE", "auto").lower()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
AI_EFFORT = os.getenv("AI_EFFORT", "medium")                 # low | medium | high
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "16000"))
AI_FALLBACKS = os.getenv("AI_FALLBACKS", "1") not in ("0", "false", "no")   # server-side refusal fallback

# Saving AI-generated questions writes into the content repo; allow turning it off for a shared deployment.
ALLOW_SAVE = os.getenv("COACH_ALLOW_SAVE", "1") not in ("0", "false", "no")
