#!/usr/bin/env bash
# Stops whatever start.sh started: the native server (its whole process group) and/or the Docker container.
cd "$(dirname "$0")"
stopped=0
if [ -f .run/app.pid ]; then
  pid="$(cat .run/app.pid)"
  if kill -0 "$pid" 2>/dev/null; then
    kill -TERM -- "-$pid" 2>/dev/null || { pkill -TERM -P "$pid" 2>/dev/null; kill -TERM "$pid" 2>/dev/null; }
    for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.25; done
    kill -0 "$pid" 2>/dev/null && { kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null; }
    echo "Stopped Interview Coach (PID $pid)."
    stopped=1
  fi
  rm -f .run/app.pid
fi

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  if [ -n "$(docker compose ps -q 2>/dev/null)" ]; then
    docker compose down
    echo "Stopped Docker container."
    stopped=1
  fi
fi

[ "$stopped" = 1 ] || echo "Nothing was running."
exit 0
