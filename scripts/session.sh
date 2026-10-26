#!/bin/bash
set +x
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"
init_paths

case "${1:-}" in
  preflight)
    [[ "${SESSION_DURATION:-}" =~ ^[1-5]$ ]] || die 'Session duration must be 1 to 5 hours.'
    [[ "${AGE_RECIPIENT:-}" =~ ^age1[0-9a-z]{58}$ ]] || die 'Set the AGE_RECIPIENT repository variable to your PUBLIC age key. See README.md.'
    sudo -n true || die 'Passwordless sudo is required on the runner.'
    command -v python3 >/dev/null || die 'Python 3 is required.'
    if ! command -v age >/dev/null; then brew install age; fi
    # Validate the Bech32 checksum before any service or user is created.
    printf 'configuration check\n' | age -r "$AGE_RECIPIENT" -o /dev/null \
      || die 'The age recipient is invalid.'
    log 'Configuration and encryption validated.'
    ;;
  setup)
    [[ "${AGE_RECIPIENT:-}" =~ ^age1[0-9a-z]{58}$ ]] || die 'Missing public encryption key.'
    [[ ! -e "$STATE_DIR" ]] || die 'Session directory already exists; start a fresh run.'
    mkdir -m 700 "$STATE_DIR"
    mkdir -m 700 "$STATE_DIR/public"
    python3 "$SCRIPT_DIR/create-admin.py"
    bash "$SCRIPT_DIR/setup-rustdesk.sh"
    python3 "$SCRIPT_DIR/encrypt-connection.py"
    log 'RustDesk started and details encrypted. GUI access still depends on macOS permissions.'
    ;;
  cleanup)
    sudo -n launchctl bootout system/com.carriez.RustDesk_service >/dev/null 2>&1 || true
    sudo -n launchctl bootout "gui/$(id -u)/com.carriez.RustDesk_server" >/dev/null 2>&1 || true
    sudo -n pkill -x RustDesk >/dev/null 2>&1 || true
    sudo -n pkill -x rustdesk >/dev/null 2>&1 || true
    sudo -n pkill -f '/ChromeRemoteDesktopHost' >/dev/null 2>&1 || true
    sudo -n pkill -x remoting_host >/dev/null 2>&1 || true
    sudo -n pkill -x 'Google Chrome' >/dev/null 2>&1 || true
    sudo -n pkill -x parsecd >/dev/null 2>&1 || true
    # init_paths restricts this to the numeric run/attempt under RUNNER_TEMP.
    if [[ -d "$STATE_DIR" && ! -L "$STATE_DIR" ]]; then rm -rf -- "$STATE_DIR"; fi
    log 'Remote processes stopped and session temp files removed. The hosted VM is discarded after the job.'
    ;;
  *) die 'Usage: session.sh preflight|setup|cleanup' ;;
esac
