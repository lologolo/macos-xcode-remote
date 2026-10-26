#!/usr/bin/env python3
"""Publish fixed diagnostic messages only, never RustDesk's raw logs or images."""
import ctypes
import os
from pathlib import Path


def display_count():
    graphics = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
    active = graphics.CGGetActiveDisplayList
    active.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32)]
    active.restype = ctypes.c_int32
    count = ctypes.c_uint32()
    if active(0, None, ctypes.byref(count)) != 0:
        raise RuntimeError("Display enumeration failed")
    return count.value


def capture_error_present(paths):
    # Read a bounded tail; these files may contain sensitive IDs or addresses.
    # Match known error categories and never return or print a log line.
    for path in paths:
        try:
            with path.open("rb") as handle:
                handle.seek(0, 2)
                size = handle.tell()
                handle.seek(max(0, size - 65536))
                tail = handle.read(65536).lower()
            if b"failed to create capturer" in tail or b"no displays" in tail:
                return True
        except OSError:
            continue
    return False


def main():
    state = Path(os.environ["STATE_DIR"])
    pid = int((state / "rustdesk-server.pid").read_text().strip())
    os.kill(pid, 0)
    if display_count() == 0:
        print("::warning::macOS reports no active display. RustDesk may connect without delivering an image.")
    log_root = Path.home() / "Library" / "Logs" / "RustDesk"
    paths = list(log_root.rglob("*.log")) if log_root.is_dir() else []
    paths.append(state / "rustdesk-server.log")
    if capture_error_present(paths):
        print("::warning::RustDesk reports a screen-capture failure. Check macOS Screen Recording permissions and the runner GUI session. Raw logs are kept private.")


if __name__ == "__main__":
    try:
        main()
    except ProcessLookupError:
        print("::warning::The RustDesk capture process has stopped. A new session is required.")
    except Exception:
        print("::warning::RustDesk display diagnostics could not be completed; this does not verify screen-capture access.")
