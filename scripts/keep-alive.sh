#!/bin/bash
set +x
set -euo pipefail
[[ "${SESSION_DURATION:-}" =~ ^[1-5]$ ]] || { printf '%s\n' 'Invalid session duration.' >&2; exit 1; }
END_TIME=$(( $(date +%s) + SESSION_DURATION * 3600 ))
caffeinate -d -i -s -t "$((SESSION_DURATION * 3600))" >/dev/null 2>&1 &
CAFFEINATE_PID=$!
trap 'kill "$CAFFEINATE_PID" >/dev/null 2>&1 || true' EXIT
while true; do
  REMAINING=$((END_TIME - $(date +%s)))
  [[ "$REMAINING" -gt 0 ]] || break
  printf 'Development session active: %s minutes remaining. Save your work before the job ends.\n' "$((REMAINING / 60))"
  sleep "$((REMAINING < 60 ? REMAINING : 60))"
done
