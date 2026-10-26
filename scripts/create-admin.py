#!/usr/bin/env python3
"""Create an administrator without writing credentials to Actions environment files."""
import json
import os
import re
import secrets
import subprocess
from pathlib import Path


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, timeout=90, check=True)


def console_identity():
    uid = os.getuid()
    if uid < 501 or Path("/dev/console").stat().st_uid != uid:
        raise RuntimeError("Not the logged-in console user")
    user = run("id", "-un").stdout.strip()
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", user) or user == "remoteadmin":
        raise RuntimeError("Unexpected console account")
    return user


def configure_console_credentials(data):
    mode = os.environ.get("CONFIGURE_CONSOLE_PASSWORD", "false").lower()
    if mode == "false":
        return
    if mode != "true":
        raise RuntimeError("Invalid console-password setting")
    # Never reset an existing user's password on a personal/persistent Mac.
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted":
        raise RuntimeError("Console-password reset requires a GitHub-hosted runner")
    user = console_identity()
    result = run("dseditgroup", "-o", "checkmember", "-m", user, "admin")
    if "yes" not in result.stdout.lower():
        raise RuntimeError("Console user is not already an administrator")
    password = secrets.token_hex(24)
    print(f"::add-mask::{password}", flush=True)
    # This is an explicit per-run opt-in. It changes the account password, not
    # the password of an existing login keychain. No logout or switch is done.
    run("sudo", "-n", "dscl", ".", "-passwd", f"/Users/{user}", password)
    run("dscl", ".", "-authonly", user, password)
    data["console_user"] = user
    data["console_password"] = password
    print("Current GUI administrator password configured and authentication verified; no session switch performed.")


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
    configure_console_credentials(data)
    with (state / "credentials.json").open("x", encoding="utf-8") as handle:
        json.dump(data, handle)
    print("Dedicated administrator created and authentication verified.")


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main()
    except Exception:
        raise SystemExit("Administrator setup failed; remote access will not be published.")
