#!/usr/bin/env bash
# Starts Java Prep Live (JDK 21+ only; no Maven, no pip).
#   ./start.sh           -> http://127.0.0.1:8090
#   ./start.sh 9000      -> choose a port
#   ./start.sh --check   -> run every example headless, print ok/FAIL, exit 1 on failure
cd "$(dirname "$0")" || exit 1
# java: PATH, else JAVA_HOME, else the newest JDK IntelliJ installed under ~/.jdks
JAVA=""
if command -v java >/dev/null 2>&1; then JAVA=java
elif [ -n "$JAVA_HOME" ] && [ -x "$JAVA_HOME/bin/java" ]; then JAVA="$JAVA_HOME/bin/java"
else
  for d in "$HOME"/.jdks/*/; do
    for b in "${d}bin/java" "${d}bin/java.exe" "${d}Contents/Home/bin/java"; do [ -x "$b" ] && JAVA="$b"; done
  done
fi
[ -n "$JAVA" ] || { echo "ERROR: Java not found (PATH, JAVA_HOME, ~/.jdks). Install JDK 21+."; exit 1; }
if [ "$1" = "--check" ]; then exec "$JAVA" JavaPrepLive.java --check; fi
PORT="${1:-${PORT:-8090}}"
echo "Starting Java Prep Live on http://127.0.0.1:${PORT}  (Ctrl+C to stop)"
exec "$JAVA" JavaPrepLive.java --port "$PORT"
