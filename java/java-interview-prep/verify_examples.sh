#!/usr/bin/env bash
# Runs every examples/**/*.java with stdout redirected (catches encoding crashes), prints ok/FAIL.
# Usage: ./verify_examples.sh [folder-glob]    e.g. ./verify_examples.sh 12_kafka
cd "$(dirname "$0")" || exit 1
pass=0; fail=0
for f in examples/${1:-*}/*.java; do
  [ -f "$f" ] || continue
  start=$(date +%s)
  if java "$f" >/dev/null 2>/tmp/verify_err.txt; then
    echo "ok   $f ($(( $(date +%s) - start ))s)"; pass=$((pass+1))
  else
    echo "FAIL $f"; head -5 /tmp/verify_err.txt; fail=$((fail+1))
  fi
done
echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ]
