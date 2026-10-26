#!/bin/bash
set +x
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"
init_paths
WORKDIR="$(mktemp -d "$STATE_DIR/google.XXXXXX")"
MOUNT_CHROME=''
MOUNT_CRD=''
cleanup() {
  if [[ -n "$MOUNT_CRD" ]]; then hdiutil detach -quiet "$MOUNT_CRD" >/dev/null 2>&1 || true; fi
  if [[ -n "$MOUNT_CHROME" ]]; then hdiutil detach -quiet "$MOUNT_CHROME" >/dev/null 2>&1 || true; fi
  rm -rf -- "$WORKDIR"
}
trap cleanup EXIT

if [[ ! -d '/Applications/Google Chrome.app' ]]; then
  log 'Downloading Google Chrome from Google.'
  download 'https://dl.google.com/chrome/mac/universal/stable/GGRO/googlechrome.dmg' "$WORKDIR/chrome.dmg"
  MOUNT_CHROME="$WORKDIR/chrome-mount"
  mkdir "$MOUNT_CHROME"
  hdiutil attach -quiet -nobrowse -readonly -mountpoint "$MOUNT_CHROME" "$WORKDIR/chrome.dmg"
  verify_google_app "$MOUNT_CHROME/Google Chrome.app"
  sudo -n ditto "$MOUNT_CHROME/Google Chrome.app" '/Applications/Google Chrome.app'
  hdiutil detach -quiet "$MOUNT_CHROME"
  MOUNT_CHROME=''
fi
verify_google_app '/Applications/Google Chrome.app'

# Reinstall the signed current host on each fresh VM; a receipt alone is not proof
# that the actual host files still exist. No Google tokens or browser profiles persist.
log 'Downloading Chrome Remote Desktop Host from Google.'
download 'https://dl.google.com/dl/chrome-remote-desktop/chromeremotedesktop.dmg' "$WORKDIR/crd.dmg"
MOUNT_CRD="$WORKDIR/crd-mount"
mkdir "$MOUNT_CRD"
hdiutil attach -quiet -nobrowse -readonly -mountpoint "$MOUNT_CRD" "$WORKDIR/crd.dmg"
PKG="$MOUNT_CRD/Chrome Remote Desktop Host.pkg"
[[ -e "$PKG" ]] || die 'Chrome Remote Desktop Host package missing.'
verify_google_pkg "$PKG"
sudo -n installer -pkg "$PKG" -target / >/dev/null
hdiutil detach -quiet "$MOUNT_CRD"
MOUNT_CRD=''
pkgutil --pkg-info com.google.pkg.ChromeRemoteDesktopHost >/dev/null \
  || die 'Chrome Remote Desktop Host receipt missing after installation.'

python3 "$SCRIPT_DIR/prepare-crd.py"
open -a '/Applications/Google Chrome.app' 'https://remotedesktop.google.com/access' --args --no-first-run >/dev/null 2>&1
log 'Chrome and Chrome Remote Desktop Host installed; GUI job registered and official consent wizard launched. Complete permissions, Google registration and PIN through RustDesk.'
