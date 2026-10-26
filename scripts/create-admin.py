#!/usr/bin/env python3
"""Create an administrator without writing credentials to Actions environment files."""
import json
import os
import secrets
import subprocess
from pathlib import Path


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, timeout=90, check=True)


def main():
    state = Path(os.environ["STATE_DIR"])
    user = "remoteadmin"
    if subprocess.run(["id", user], capture_output=True).returncode == 0:
        raise RuntimeError("Existing account")
    password = secrets.token_hex(24)
    print(f"::add-mask::{password}", flush=True)
    # sysadminctl requires a password argument for noninteractive creation. It is
    # briefly visible to local privileged processes, part of the runner trust boundary.
    run("sudo", "-n", "sysadminctl", "-addUser", user, "-fullName",
        "Remote Development Admin", "-password", password, "-admin")
    run("id", user)  # sysadminctl may return zero even on an unsuccessful operation.
    result = run("dseditgroup", "-o", "checkmember", "-m", user, "admin")
    if "yes" not in result.stdout.lower():
        raise RuntimeError("Admin membership missing")
    run("sudo", "-n", "createhomedir", "-c", "-u", user)
    home = Path("/Users") / user
    if not home.is_dir():
        raise RuntimeError("Home directory missing")
    run("sudo", "-n", "chmod", "700", str(home))
    run("dscl", ".", "-authonly", user, password)
    data = {"macos_user": user, "macos_password": password,
            "rustdesk_password": secrets.token_hex(24)}
    print(f"::add-mask::{data['rustdesk_password']}", flush=True)
    with (state / "credentials.json").open("x", encoding="utf-8") as handle:
        json.dump(data, handle)
    print("Dedicated administrator created and authentication verified.")


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main()
    except Exception:
        raise SystemExit("Administrator setup failed; remote access will not be published.")
