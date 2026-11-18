"""All runtime settings in one place (env-driven, no extra dependency).

Values are read from the process environment, falling back to a git-ignored `.env`
file in the project root. Relative paths are resolved against the project root, not
the current working directory, so `uvicorn` can be started from anywhere.
"""
import os
import sys
from pathlib import Path

from prepkit.env import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")                    # real environment variables always win

# Folder that contains 01_python_core/, 02_concurrency/ ... (python-interview-prep/)
PREP_ROOT = (BASE_DIR / os.getenv("PREP_ROOT", "../python-interview-prep")).resolve()
RUN_TIMEOUT_S = int(os.getenv("RUN_TIMEOUT_S", "60"))
MAX_OUTPUT_BYTES = int(os.getenv("MAX_OUTPUT_BYTES", str(1_000_000)))
MAX_PARALLEL_RUNS = int(os.getenv("MAX_PARALLEL_RUNS", "2"))
# Editing + running arbitrary code is OFF by default. Only enable on localhost.
ALLOW_EDIT = os.getenv("PREP_ALLOW_EDIT", "0") == "1"
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
# Java/Python twins (shared/cross-stack-pairs.md) and where the Java runner listens, for "Same idea in Java"
PAIRS_FILE = (BASE_DIR / os.getenv("PAIRS_FILE", "../../shared/cross-stack-pairs.md")).resolve()
JAVAPREP_URL = os.getenv("JAVAPREP_URL", "http://127.0.0.1:8090").rstrip("/")
PYTHON_VERSION = ".".join(map(str, sys.version_info[:3]))
