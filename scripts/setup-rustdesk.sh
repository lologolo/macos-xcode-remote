#!/bin/bash
set +x
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"
init_paths
[[ -f "$STATE_DIR/credentials.json" ]] || die 'Create the session credentials first.'

# Explicit release and independently checked GitHub release asset digests.
VERSION=1.5.0
case "$(uname -m)" in
  arm64) ARCH=aarch64; DIGEST=3929b0a4321e7d0f561a317059798be882d65decc59681eb77061f8efe56fbf4 ;;
  x86_64) ARCH=x86_64; DIGEST=1ca3cbfbe7f2bd28b50c93fcd50d4a0b671dc76d18be27cea99d3a65767eb526 ;;
  *) die 'Unsupported CPU architecture.' ;;
esac
WORKDIR="$(mktemp -d "$STATE_DIR/rustdesk.XXXXXX")"
MOUNT=''
cleanup() {
  if [[ -n "$MOUNT" ]]; then hdiutil detach -quiet "$MOUNT" >/dev/null 2>&1 || true; fi
  rm -rf -- "$WORKDIR"
}
trap cleanup EXIT
log "Installing verified RustDesk $VERSION ($ARCH)."
download "https://github.com/rustdesk/rustdesk/releases/download/$VERSION/rustdesk-$VERSION-$ARCH.dmg" "$WORKDIR/rustdesk.dmg"
printf '%s  %s\n' "$DIGEST" "$WORKDIR/rustdesk.dmg" | shasum -a 256 -c - >/dev/null \
  || die 'RustDesk download checksum mismatch.'
MOUNT="$WORKDIR/mount"
mkdir "$MOUNT"
hdiutil attach -quiet -nobrowse -readonly -mountpoint "$MOUNT" "$WORKDIR/rustdesk.dmg"
[[ -d "$MOUNT/RustDesk.app" ]] || die 'RustDesk app missing from image.'
codesign --verify --deep --strict "$MOUNT/RustDesk.app" >/dev/null 2>&1 || die 'Invalid RustDesk code signature.'
spctl --assess --type execute "$MOUNT/RustDesk.app" >/dev/null 2>&1 || die 'Gatekeeper rejected RustDesk.'
sudo -n ditto "$MOUNT/RustDesk.app" /Applications/RustDesk.app
sudo -n chown -R root:wheel /Applications/RustDesk.app
hdiutil detach -quiet "$MOUNT"
MOUNT=''

# Configure password-only access before any service can accept a connection.
USER_CONFIG="$HOME/Library/Preferences/com.carriez.RustDesk"
ROOT_CONFIG='/var/root/Library/Preferences/com.carriez.RustDesk'
mkdir -p "$USER_CONFIG"
chmod 700 "$USER_CONFIG"
install -m 600 "$SCRIPT_DIR/../configs/rustdesk-options.toml" "$USER_CONFIG/RustDesk2.toml"
sudo -n mkdir -p "$ROOT_CONFIG"
sudo -n chmod 700 "$ROOT_CONFIG"
sudo -n install -o root -g wheel -m 600 "$SCRIPT_DIR/../configs/rustdesk-options.toml" "$ROOT_CONFIG/RustDesk2.toml"

# Upstream 1.5.0 launchd definitions, vendored for review rather than fetched at runtime.
sudo -n install -o root -g wheel -m 644 "$SCRIPT_DIR/../configs/rustdesk-daemon.plist" /Library/LaunchDaemons/com.carriez.RustDesk_service.plist
sudo -n install -o root -g wheel -m 644 "$SCRIPT_DIR/../configs/rustdesk-agent.plist" /Library/LaunchAgents/com.carriez.RustDesk_server.plist
sudo -n launchctl bootstrap system /Library/LaunchDaemons/com.carriez.RustDesk_service.plist
sudo -n launchctl bootstrap "gui/$(id -u)" /Library/LaunchAgents/com.carriez.RustDesk_server.plist
python3 "$SCRIPT_DIR/configure-rustdesk.py"
open -a /Applications/RustDesk.app >/dev/null 2>&1
log 'RustDesk configured. Screen/input permissions must be supported and granted by macOS.'
