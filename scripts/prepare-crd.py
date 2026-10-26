#!/usr/bin/env python3
"""Register Google's installed jobs in the GUI and open its consent wizard.

No Google tokens, PINs, password arguments or TCC database changes are used.
"""
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path, PurePosixPath

MANIFEST = Path("/Library/Google/Chrome/NativeMessagingHosts/com.google.chrome.remote_desktop.json")
AGENT = Path("/Library/LaunchAgents/org.chromium.chromoting.plist")
BROKER = Path("/Library/LaunchDaemons/org.chromium.chromoting.broker.plist")


def launchctl(*args, privileged=False):
    command = (["sudo", "-n"] if privileged else []) + ["launchctl", *args]
    return subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, timeout=20).returncode


def ensure_job(domain, label, plist, privileged=False):
    target = f"{domain}/{label}"
    if launchctl("enable", target, privileged=privileged) != 0:
        raise RuntimeError("Unable to enable the installed Google job.")
    if launchctl("print", target, privileged=privileged) != 0:
        # Fresh root CLI installs may omit the current user's LaunchAgent.
        # Recheck after bootstrap to handle an installer loading it concurrently.
        launchctl("bootstrap", domain, str(plist), privileged=privileged)
        if launchctl("print", target, privileged=privileged) != 0:
            raise RuntimeError("The installed Google job is not registered in the expected session.")


def native_host_path(manifest):
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("name") != "com.google.chrome.remote_desktop":
        raise RuntimeError("Unexpected Chrome Remote Desktop manifest.")
    raw_path = data["path"]
    path = PurePosixPath(raw_path)
    if not path.is_absolute() or ".." in path.parts or not str(path).startswith("/Library/PrivilegedHelperTools/"):
        raise RuntimeError("Unexpected Chrome Remote Desktop native host location.")
    return Path(raw_path)


def open_wizard(native_host, state):
    # Run in the console user's GUI context. Running this as root would check
    # the wrong permission scope and could leave the dialog invisible.
    with (state / "crd-permission-wizard.log").open("ab") as output:
        process = subprocess.Popen([str(native_host), "--check-permission"],
                                   stdin=subprocess.DEVNULL, stdout=output,
                                   stderr=subprocess.STDOUT, close_fds=True)
    (state / "crd-permission-wizard.pid").write_text(str(process.pid), encoding="utf-8")


def write_shortcut():
    desktop = Path.home() / "Desktop"
    desktop.mkdir(exist_ok=True)
    shortcut = desktop / "Chrome Remote Desktop - Permessi.command"
    if shortcut.is_symlink():
        raise RuntimeError("Unexpected shortcut symlink.")
    command = "exec " + shlex.quote(sys.executable) + " " + shlex.quote(str(Path(__file__).resolve()))
    shortcut.write_text("#!/bin/bash\nset +x\n" + command + "\n", encoding="utf-8")
    shortcut.chmod(0o700)


def main():
    if sys.platform != "darwin" or os.geteuid() == 0:
        raise RuntimeError("Open this helper as the logged-in macOS user, without sudo.")
    uid = os.getuid()
    if Path("/dev/console").stat().st_uid != uid:
        raise RuntimeError("The current user is not the logged-in console user.")
    if not AGENT.is_file():
        raise RuntimeError("Google's LaunchAgent is missing; reinstall the signed Host package.")
    native_host = native_host_path(MANIFEST)
    if not native_host.is_file() or not os.access(native_host, os.X_OK):
        raise RuntimeError("The native Host executable is missing; reinstall the signed Host package.")
    state = Path(os.environ.get("STATE_DIR", str(Path.home() / "Library/Logs/MacRemote")))
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    if state.is_symlink():
        raise RuntimeError("Unexpected diagnostic directory symlink.")
    state.chmod(0o700)
    ensure_job(f"gui/{uid}", "org.chromium.chromoting", AGENT)
    # Recent Host versions also install a system broker; older versions may not.
    if BROKER.is_file():
        ensure_job("system", "org.chromium.chromoting.broker", BROKER, privileged=True)
    write_shortcut()
    open_wizard(native_host, state)
    print("Google Host registered in the console session. Complete Google's Accessibility and Screen Recording wizard through RustDesk.")
    print("Then return to remotedesktop.google.com/access and finish registration with your Google account and PIN.")
    print("When macOS asks for an administrator, use remoteadmin and the macOS password from your decrypted file.")
    print("This preparation does not confirm Google enrollment or a successful remote connection.")


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main()
    except RuntimeError as error:
        # These are our fixed diagnostic messages, not subprocess output.
        print(f"Chrome Remote Desktop preparation: {error}", file=sys.stderr)
        raise SystemExit(1)
    except Exception:
        # Fixed message only: native-messaging/installer diagnostics may contain
        # identifiers or tokens and must not be copied to public Actions logs.
        print("Chrome Remote Desktop preparation failed. Check the installed Host and console session locally through RustDesk; no permissions were bypassed.", file=sys.stderr)
        raise SystemExit(1)
