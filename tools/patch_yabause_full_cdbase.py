#!/usr/bin/env python3
"""Stage80: generate a strictly pinned, instrumented whole Yabause cdbase.c.

Only a fixed PUBLIC third-party C source file is accepted. The program
does not access Saturn discs/BIOS, execute Yabause, or export game media.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.check_yabause_upstream_callback import (
    UPSTREAM_BLOB, UPSTREAM_COMMIT, validate_upstream_source,
    extract_primary_read_callback,
)
from tools.saturn_yabause_cdbase_hook import FUNCTION, FOLLOWING


def patch_full_cdbase(raw: bytes) -> bytes:
    source = validate_upstream_source(raw)
    if source.count(FUNCTION) != 1:
        raise ValueError("ambiguous pinned callback start")
    start = source.index(FUNCTION)
    if source.count(FOLLOWING) != 1:
        raise ValueError("ambiguous pinned callback boundary")
    end = source.index(FOLLOWING, start + len(FUNCTION))
    if not start < end:
        raise ValueError("malformed pinned callback boundary")
    # Stage79 instruments the real pinned callback, already requiring all
    # five primary data read patterns. Everything outside stays byte-identical.
    patched_callback = extract_primary_read_callback(source)
    modified = source[:start] + patched_callback + source[end:]
    if modified == source or modified[:start] != source[:start]:
        raise ValueError("unexpected patch boundary")
    if modified[start + len(patched_callback):] != source[end:]:
        raise ValueError("outside-callback mutation")
    if (modified.count("VH_SATURN_CAPTURE_GATE") != 1 or
            modified.count("if (vh_primary_read == 1)") != 1 or
            modified.count("vh_primary_read = (num_read = fread(") != 5):
        raise ValueError("incomplete primary-data read instrumentation")
    return modified.encode("utf-8")


def create_patched_source(source: Path, output: Path) -> dict:
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError("cannot overwrite the source or existing output")
    if source.name != "cdbase.c" or output.suffix != ".c":
        raise ValueError("expected pinned cdbase.c input and C output")
    patched = patch_full_cdbase(source.read_bytes())
    # Restrict accidental world-readable output. Source is public, but this
    # utility is also meant for local private research installations.
    with output.open("xb") as stream:
        stream.write(patched)
    return {
        "stage": 80,
        "source": "pinned_public_yabause_cdbase",
        "source_commit": UPSTREAM_COMMIT,
        "source_git_blob": UPSTREAM_BLOB,
        "patched_entire_upstream_translation_unit": True,
        "outside_callback_preserved": True,
        "primary_data_read_sites": 5,
        "game_media_used": False,
        "full_core_compiled": False,
        "original_saturn_game_executed": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        report = create_patched_source(args.source, args.output)
        print(json.dumps(report, sort_keys=True))
        return 0
    except (ValueError, OSError, TypeError, UnicodeError):
        print("STAGE80_PINNED_FULL_SOURCE_PATCH_REJECTED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
