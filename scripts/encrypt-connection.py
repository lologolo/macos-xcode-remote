#!/usr/bin/env python3
"""Only ciphertext is written inside the artifact directory."""
import json
import os
import subprocess
from pathlib import Path


def main():
    state = Path(os.environ["STATE_DIR"])
    source = state / "credentials.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    console_info = ""
    if data.get("console_user") and data.get("console_password"):
        console_info = (
            "CURRENT GUI ACCOUNT (for dialogs that prefill the logged-in user):\n"
            f"macOS console user: {data['console_user']}\n"
            f"macOS console password: {data['console_password']}\n"
            "Keep the current GUI session open; use this password when that account is prefilled.\n"
            "The existing login keychain may retain its previous password.\n\n"
        )
    text = (
        f"Run: {os.environ['GITHUB_RUN_ID']} / attempt {os.environ['GITHUB_RUN_ATTEMPT']}\n"
        f"RustDesk ID: {data['rustdesk_id']}\n"
        f"RustDesk password: {data['rustdesk_password']}\n\n"
        + console_info +
        "ADDITIONAL ADMINISTRATOR (also available as a fallback):\n"
        f"macOS administrator: {data['macos_user']}\n"
        f"macOS password: {data['macos_password']}\n\n"
        "Connect with RustDesk. Chrome and Chrome Remote Desktop Host are installed in a later step.\n"
        "Open https://remotedesktop.google.com/access and complete Google registration, PIN and macOS permissions.\n"
        "Admin authentication does not bypass TCC, Secure Token or VM restrictions.\n"
        "Check the workflow step outcome to confirm the Google installation succeeded.\n"
    )
    target = state / "public" / "connection-info.txt.age"
    try:
        subprocess.run(["age", "-r", os.environ["AGE_RECIPIENT"], "-o", str(target)],
                       input=text.encode(), capture_output=True, check=True, timeout=30)
        if target.stat().st_size < 100:
            raise RuntimeError("Empty ciphertext")
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        source.unlink(missing_ok=True)


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main()
    except Exception:
        raise SystemExit("Connection encryption failed; no credentials will be uploaded.")
