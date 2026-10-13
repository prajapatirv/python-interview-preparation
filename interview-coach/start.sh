#!/usr/bin/env bash
# Starts the Interview Coach in the background.
#   ./start.sh              creates .venv, installs deps, runs uvicorn
#   ./start.sh --install    force re-install of dependencies
# Env (or .env): PORT (8100), ANTHROPIC_API_KEY, AI_MODE (auto|claude|mock), ANTHROPIC_MODEL, AI_EFFORT.
# With no API key the coach runs in offline mock mode.
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8100}"
URL="http://127.0.0.1:${PORT}"
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --install) FORCE=1 ;;
    *) echo "unknown argument: $arg (use: --install)"; exit 2 ;;
  esac
done

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "Created .env from .env.example - put your ANTHROPIC_API_KEY there for the real AI coach."
fi
if [ -f .run/app.pid ] && kill -0 "$(cat .run/app.pid)" 2>/dev/null; then
  echo "Already running (PID $(cat .run/app.pid)): $URL   -- run ./stop.sh first to restart."
  exit 0
fi

PYBIN=""
for cand in python3 python py; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    PYBIN="$cand"; break
  fi
done
[ -n "$PYBIN" ] || { echo 'ERROR: Python 3.10+ not found.' >&2; exit 1; }

if [ -x .venv/bin/python ]; then VPY=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then VPY=.venv/Scripts/python.exe     # Git Bash on Windows
else
  echo "Creating virtual environment..."
  "$PYBIN" -m venv .venv
  if [ -x .venv/bin/python ]; then VPY=.venv/bin/python; else VPY=.venv/Scripts/python.exe; fi
  FORCE=1
fi
[ -f .venv/.deps-ok ] || FORCE=1
if [ "$FORCE" = 1 ]; then
  echo "Installing dependencies (first run takes a minute)..."
  "$VPY" -m pip install -q --disable-pip-version-check -r requirements-dev.txt
  echo ok > .venv/.deps-ok
fi

mkdir -p .run
echo "Starting server on $URL ..."
if command -v setsid >/dev/null 2>&1; then
  setsid nohup "$VPY" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" >.run/app.log 2>&1 < /dev/null &
else
  nohup "$VPY" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" >.run/app.log 2>&1 < /dev/null &
fi
echo $! > .run/app.pid

for _ in $(seq 1 60); do
  if "$VPY" -c "import urllib.request as u; u.urlopen('$URL/api/status', timeout=2)" 2>/dev/null; then
    echo; echo "Ready: $URL   (logs: .run/app.log, stop with ./stop.sh)"
    exit 0
  fi
  sleep 0.5
done
echo "ERROR: server did not become ready. Last log lines:" >&2
tail -n 15 .run/app.log >&2 || true
bash ./stop.sh >/dev/null 2>&1 || true
exit 1
