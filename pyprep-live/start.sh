#!/usr/bin/env bash
# Starts the Live Runner in the background.
#   ./start.sh              native: creates .venv, installs deps, runs uvicorn (default)
#   ./start.sh docker       local Docker: docker compose up -d --build
#   ./start.sh --install    force re-install of dependencies (native)
# Env: PORT (8000), PREP_ROOT, PREP_ALLOW_EDIT (1 here: local tool), AI_MODE (auto|claude|mock),
#      ANTHROPIC_API_KEY (or put it in .env). With no key the AI coach runs in mock mode.
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8000}"
export PREP_ALLOW_EDIT="${PREP_ALLOW_EDIT:-1}"
URL="http://127.0.0.1:${PORT}"
MODE=native
FORCE=0
for arg in "$@"; do
  case "$arg" in
    docker) MODE=docker ;;
    --install) FORCE=1 ;;
    *) echo "unknown argument: $arg (use: docker | --install)"; exit 2 ;;
  esac
done

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "Created .env from .env.example (no API key = mock AI mode)."
fi
if [ ! -d ../python-interview-prep ] && [ -z "${PREP_ROOT:-}" ]; then
  echo "ERROR: ../python-interview-prep not found. Set PREP_ROOT to the examples folder." >&2
  exit 1
fi

wait_ready() {   # up to ~30 s
  for _ in $(seq 1 60); do
    if command -v curl >/dev/null 2>&1; then
      curl -fsS -o /dev/null --max-time 2 "$URL/api/catalog" 2>/dev/null && return 0
    elif "$PY" -c "import urllib.request as u; u.urlopen('$URL/api/catalog', timeout=2)" 2>/dev/null; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

open_browser() {
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then open "$URL" || true
  elif command -v cmd.exe >/dev/null 2>&1; then cmd.exe /c start "" "$URL" >/dev/null 2>&1 || true
  fi
}

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python

if [ "$MODE" = docker ]; then
  docker info >/dev/null 2>&1 || { echo 'ERROR: Docker is not running. Start it, or run ./start.sh without "docker".' >&2; exit 1; }
  echo "Building and starting the container (first build takes a few minutes)..."
  PORT="$PORT" docker compose up -d --build
  if ! wait_ready; then echo "ERROR: container did not become ready." >&2; docker compose logs --tail 30; exit 1; fi
  echo; echo "Ready: $URL   (Docker; stop with ./stop.sh)"
  open_browser
  exit 0
fi

# ------------------------------------------------------------------ native
if [ -f .run/app.pid ] && kill -0 "$(cat .run/app.pid)" 2>/dev/null; then
  echo "Already running (PID $(cat .run/app.pid)): $URL   -- run ./stop.sh first to restart."
  exit 0
fi

# a usable Python 3.10+ (python3 or python)
PYBIN=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    PYBIN="$cand"; break
  fi
done
[ -n "$PYBIN" ] || { echo 'ERROR: Python 3.10+ not found. Install it, or run: ./start.sh docker' >&2; exit 1; }

if [ -x .venv/bin/python ]; then VPY=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then VPY=.venv/Scripts/python.exe     # Git Bash on Windows
else
  echo "Creating virtual environment..."
  "$PYBIN" -m venv .venv
  if [ -x .venv/bin/python ]; then VPY=.venv/bin/python; else VPY=.venv/Scripts/python.exe; fi
  FORCE=1
fi
PY="$VPY"
[ -f .venv/.deps-ok ] || FORCE=1
if [ "$FORCE" = 1 ]; then
  echo "Installing dependencies (first run takes a minute)..."
  "$VPY" -m pip install -q --disable-pip-version-check -r requirements.txt -r requirements-examples.txt
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

if ! wait_ready; then
  echo "ERROR: server did not become ready. Last log lines:" >&2
  tail -n 15 .run/app.log >&2 || true
  bash ./stop.sh >/dev/null 2>&1 || true
  exit 1
fi
echo; echo "Ready: $URL   (logs: .run/app.log, stop with ./stop.sh)"
open_browser
