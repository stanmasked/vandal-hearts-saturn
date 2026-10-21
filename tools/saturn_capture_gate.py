#!/usr/bin/env python3
"""Stage77: manually open or close a PRIVATE numeric CD-read capture window.

The marker is only an operator-controlled hint. It does not read emulator
screens, provide trusted frame times, or authenticate independent captures.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
import sys
import tempfile

MARKER = b"1\n"


def set_capture_gate(path: Path, enabled: bool) -> None:
    if (not isinstance(path, Path) or path.suffix != ".vhgate"
            or type(enabled) is not bool):
        raise ValueError("invalid gate file or operation")
    if not path.is_absolute() or path.is_symlink() or not path.parent.is_dir():
        raise ValueError("gate must be a private absolute regular file path")

    if enabled:
        if path.exists():
            raise ValueError("gate file already exists")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="wb", dir=str(path.parent), prefix=".vhgate-",
                    suffix=".tmp", delete=False) as stream:
                temporary = stream.name
                os.fchmod(stream.fileno(), stat.S_IRUSR | stat.S_IWUSR)
                stream.write(MARKER)
                stream.flush()
                os.fsync(stream.fileno())
            if path.exists() or path.is_symlink():
                raise ValueError("gate destination appeared during activation")
            os.replace(temporary, path)
        finally:
            if temporary is not None and os.path.exists(temporary):
                os.unlink(temporary)
    else:
        if path.is_symlink() or not path.is_file():
            raise ValueError("gate is not open")
        if path.read_bytes() != MARKER:
            raise ValueError("refusing to delete unexpected gate content")
        path.unlink()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gate", required=True, type=Path)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--start", action="store_true")
    mode.add_argument("--stop", action="store_true")
    args = p.parse_args()
    try:
        set_capture_gate(args.gate, enabled=args.start)
    except (OSError, ValueError, TypeError) as exc:
        print("VH_CAPTURE_GATE_REJECTED " + type(exc).__name__, file=sys.stderr)
        return 1
    print("VH_CAPTURE_GATE_" + ("OPEN" if args.start else "CLOSED") +
          " screen_phase_verified=false frame_sync_verified=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
