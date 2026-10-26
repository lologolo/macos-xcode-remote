#!/usr/bin/env python3
"""Use supported RustDesk CLI; never print its output or configuration files."""
import json
import os
import re
import subprocess
import time
from pathlib import Path

CLI = "/Applications/RustDesk.app/Contents/MacOS/RustDesk"


def command(*args):
    result = subprocess.run(["sudo", "-n", CLI, *args], capture_output=True,
                            text=True, timeout=15, check=True)
    return result.stdout.strip()


def main():
    path = Path(os.environ["STATE_DIR"]) / "credentials.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    # Some CLI failures return status zero, so require explicit acknowledgement.
    for attempt in range(12):
        try:
            if command("--password", data["rustdesk_password"]) == "Done!":
                break
        except (subprocess.SubprocessError, OSError):
            pass
        time.sleep(3)
    else:
        raise RuntimeError("Password not set")
    options = {
        "approve-mode": "password",
        "verification-method": "use-permanent-password",
        "direct-server": "N",
        "enable-lan-discovery": "N",
        "enable-tunnel": "N",
        "enable-terminal": "N",
    }
    for key, value in options.items():
        command("--option", key, value)
        # IPC changes can be asynchronous. Confirm persistence before publishing.
        for attempt in range(5):
            if command("--option", key) == value:
                break
            time.sleep(1)
        else:
            raise RuntimeError("Option not applied")
    for attempt in range(20):
        ident = command("--get-id").replace(" ", "")
        if re.fullmatch(r"[0-9]{6,16}", ident):
            break
        time.sleep(3)
    else:
        raise RuntimeError("No valid host ID")
    print(f"::add-mask::{ident}", flush=True)
    data["rustdesk_id"] = ident
    path.write_text(json.dumps(data), encoding="utf-8")
    print("RustDesk password, access settings and host ID configured.")


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main()
    except Exception:
        raise SystemExit("RustDesk configuration failed; connection details will not be published.")
