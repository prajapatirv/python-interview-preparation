#!/usr/bin/env bash
# Creates .venv at the workspace root with everything every Python check needs, then runs them all.
# Same steps as CI (.github/workflows/ci.yml). Usage: ./dev-setup.sh [--no-checks]
cd "$(dirname "$0")" || exit 1
if [ -x .venv/Scripts/python.exe ]; then PY="$PWD/.venv/Scripts/python.exe"      # Git Bash on Windows
elif [ -x .venv/bin/python ]; then PY="$PWD/.venv/bin/python"
else
  if command -v py >/dev/null; then py -3.14 -m venv .venv || py -m venv .venv; else python3 -m venv .venv; fi || exit 1
  if [ -x .venv/Scripts/python.exe ]; then PY="$PWD/.venv/Scripts/python.exe"; else PY="$PWD/.venv/bin/python"; fi
fi
"$PY" -m pip install -q --disable-pip-version-check -r requirements-dev.txt || exit 1
[ "$1" = "--no-checks" ] && exit 0

fail=0
step() { echo "== $1"; shift; "$@" || fail=1; }
step ruff                  "$PY" -m ruff check .
step prepkit               bash -c "cd shared/prepkit && '$PY' -m pytest -q"
step interview-coach       bash -c "cd interview-coach && '$PY' -m pytest -q"
step pyprep-live           bash -c "cd python/pyprep-live && '$PY' -m pytest -q"
step python-interview-prep bash -c "cd python/python-interview-prep && '$PY' -m pytest -q"
step examples              "$PY" scripts/verify_examples.py
step "QUESTION_INDEX links" "$PY" scripts/check_content.py
echo
if [ $fail -ne 0 ]; then echo "SOME CHECKS FAILED"; exit 1; fi
echo "all checks passed"
