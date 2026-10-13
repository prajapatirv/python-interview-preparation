#!/usr/bin/env bash
# Stops the server that start.sh started (its whole process group).
cd "$(dirname "$0")"
if [ -f .run/app.pid ]; then
  pid="$(cat .run/app.pid)"
  if kill -0 "$pid" 2>/dev/null; then
    kill -TERM -- "-$pid" 2>/dev/null || { pkill -TERM -P "$pid" 2>/dev/null; kill -TERM "$pid" 2>/dev/null; }
    for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.25; done
    kill -0 "$pid" 2>/dev/null && { kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null; }
    echo "Stopped Interview Coach (PID $pid)."
    rm -f .run/app.pid
    exit 0
  fi
  rm -f .run/app.pid
fi
echo "Nothing was running."
