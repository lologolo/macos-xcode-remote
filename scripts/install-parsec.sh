#!/bin/bash
set +x
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"
init_paths
WORKDIR="$(mktemp -d "$STATE_DIR/parsec.XXXXXX")"
trap 'rm -rf -- "$WORKDIR"' EXIT
download 'https://builds.parsec.app/package/parsec-macos.pkg' "$WORKDIR/parsec.pkg"
pkgutil --check-signature "$WORKDIR/parsec.pkg" >/dev/null 2>&1 || die 'Invalid Parsec signature.'
spctl --assess --type install "$WORKDIR/parsec.pkg" >/dev/null 2>&1 || die 'Gatekeeper rejected Parsec.'
sudo -n installer -pkg "$WORKDIR/parsec.pkg" -target / >/dev/null
[[ -d /Applications/Parsec.app ]] || die 'Parsec app missing after installation.'
log 'Parsec installed. Sign in and grant permissions manually through RustDesk to compare latency.'
