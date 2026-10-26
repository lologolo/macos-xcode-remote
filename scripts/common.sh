#!/bin/bash
# Shared scripts are compatible with macOS Bash 3.2.
set +x
set -euo pipefail
umask 077
die() { printf '%s\n' "ERROR: $*" >&2; exit 1; }
log() { printf '%s\n' "$*"; }

init_paths() {
  [[ "$(uname -s)" == Darwin ]] || die 'A macOS runner is required.'
  [[ "${GITHUB_RUN_ID:-}" =~ ^[0-9]+$ ]] || die 'Missing run ID.'
  [[ "${GITHUB_RUN_ATTEMPT:-}" =~ ^[0-9]+$ ]] || die 'Missing run attempt.'
  [[ "${RUNNER_TEMP:-}" == /* && -d "$RUNNER_TEMP" ]] || die 'Invalid runner temp directory.'
  STATE_DIR="$RUNNER_TEMP/mac-remote-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
  export STATE_DIR
}

download() {
  curl --fail --location --silent --show-error --retry 3 \
    --proto '=https' --proto-redir '=https' --connect-timeout 30 --max-time 600 "$1" -o "$2"
}

verify_google_app() {
  codesign --verify --deep --strict "$1" >/dev/null 2>&1 || die 'Invalid Chrome code signature.'
  codesign -dv --verbose=4 "$1" 2>&1 | grep -qx 'TeamIdentifier=EQHXZ8M8AV' \
    || die 'Unexpected Chrome signing team.'
  spctl --assess --type execute "$1" >/dev/null 2>&1 || die 'Gatekeeper rejected Chrome.'
}

verify_google_pkg() {
  pkgutil --check-signature "$1" 2>/dev/null | grep -Fq 'Developer ID Installer: Google LLC (EQHXZ8M8AV)' \
    || die 'Unexpected or invalid Google installer signature.'
  spctl --assess --type install "$1" >/dev/null 2>&1 || die 'Gatekeeper rejected the Google installer.'
}
