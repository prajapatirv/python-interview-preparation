#!/usr/bin/env bash
# Starts Java Prep Live (JDK 21+ only; no Maven, no pip).
#   ./start.sh           -> http://127.0.0.1:8090
#   ./start.sh 9000      -> choose a port
#   ./start.sh --check   -> run every example headless, print ok/FAIL, exit 1 on failure
cd "$(dirname "$0")" || exit 1
command -v java >/dev/null 2>&1 || { echo "ERROR: java not found on PATH (need JDK 21+)"; exit 1; }
if [ "$1" = "--check" ]; then exec java JavaPrepLive.java --check; fi
PORT="${1:-${PORT:-8090}}"
echo "Starting Java Prep Live on http://127.0.0.1:${PORT}  (Ctrl+C to stop)"
exec java JavaPrepLive.java --port "$PORT"
