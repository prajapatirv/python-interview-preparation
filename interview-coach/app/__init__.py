"""Makes the shared ``prepkit`` package importable on a local run (no install needed).

Docker images ``pip install`` it, so the import succeeds there and nothing is added to ``sys.path``.
"""
import sys
from pathlib import Path

try:
    import prepkit  # noqa: F401
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared" / "prepkit"))
