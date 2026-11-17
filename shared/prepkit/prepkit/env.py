"""Minimal ``.env`` support, so neither app needs python-dotenv."""
import os
from pathlib import Path


def load_dotenv(path: Path) -> None:
    """Loads ``KEY=value`` lines into ``os.environ``. Real environment variables always win, and a
    value that is empty after stripping quotes is ignored, so ``KEY=""`` keeps the app's default."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key.strip(), value)
