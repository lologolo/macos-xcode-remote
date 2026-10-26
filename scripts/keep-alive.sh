#!/bin/bash
set +x
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"
init_paths
[[ "${SESSION_DURATION:-}" =~ ^[1-5]$ ]] || { printf '%s\n' 'Invalid session duration.' >&2; exit 1; }
END_TIME=$(( $(date +%s) + SESSION_DURATION * 3600 ))
# Also generate a user-activity event to wake a display that already went idle.
caffeinate -u -d -i -s -t "$((SESSION_DURATION * 3600))" >/dev/null 2>&1 &
CAFFEINATE_PID=$!
trap 'kill "$CAFFEINATE_PID" >/dev/null 2>&1 || true' EXIT
while true; do
  REMAINING=$((END_TIME - $(date +%s)))
  [[ "$REMAINING" -gt 0 ]] || break
  printf 'Development session active: %s minutes remaining. Save your work before the job ends.\n' "$((REMAINING / 60))"
  python3 "$SCRIPT_DIR/rustdesk-health.py"
  sleep "$((REMAINING < 60 ? REMAINING : 60))"
done
