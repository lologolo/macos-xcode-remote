#!/bin/bash
set +x
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"
init_paths
[[ -d "$STATE_DIR" && ! -L "$STATE_DIR" ]] || die 'Session directory is missing.'
CLI='/Applications/RustDesk.app/Contents/MacOS/RustDesk'
[[ -x "$CLI" ]] || die 'RustDesk executable is missing.'

# A graphical server owned by another account is not a usable capture context.
CONSOLE_UID="$(stat -f '%u' /dev/console)"
[[ "$CONSOLE_UID" == "$(id -u)" ]] || die 'The runner is not the logged-in console user. A graphical session is required.'
pgrep -x WindowServer >/dev/null || die 'No macOS WindowServer is running.'
caffeinate -u -t 5 >/dev/null 2>&1 &

# Start directly as a child of the workflow shell, like the original working
# approach. No launchd, sudo, nohup, re-signing or TCC database changes.
"$CLI" --server >"$STATE_DIR/rustdesk-server.log" 2>&1 &
SERVER_PID=$!
printf '%s\n' "$SERVER_PID" >"$STATE_DIR/rustdesk-server.pid"
sleep 3
kill -0 "$SERVER_PID" >/dev/null 2>&1 || die 'RustDesk capture process exited during startup.'
python3 "$SCRIPT_DIR/rustdesk-health.py"
log 'RustDesk server started in the runner console session. First-frame delivery still requires a client test.'
