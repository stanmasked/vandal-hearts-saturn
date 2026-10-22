#!/usr/bin/env python3
"""Stage107 private A/B witness check for actual Saturn START input sessions.

Only compares evidence; does not detect game menu content, does not publish
game images, original BIN/CUE or original FAD records, and does not invent
frame/CD synchronization. Run with two privately captured 13200-frame
Yabause sessions: one control and one with START after frame 12000.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from tools.saturn_private_capture_cohort import _private_directory, _private_regular
from tools.saturn_private_frame_witness import validate_png_file

FAD = re.compile(rb"VHCD_FAD (0|[1-9][0-9]*)\Z")
FRAME_COUNT = 13200
PRESS_AT = 12000
RELEASE_AT = PRESS_AT + 6
MAX_FAD_BYTES = 4 * 1024 * 1024
MAX_PNG_BYTES = 8 * 1024 * 1024
CONTROL = f"VH_PAD mode=0 completed_frames={FRAME_COUNT}\n".encode()
START = (
    f"VH_PAD frame={PRESS_AT} button=START action=PRESS\n"
    f"VH_PAD frame={RELEASE_AT} button=START action=RELEASE\n"
    f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n"
).encode()


def _count_canonical_fads(directory: Path) -> tuple[int, bytes]:
    payload = _private_regular(directory / "fad.vhcdlog", MAX_FAD_BYTES)
    if not payload.endswith(b"\n") or b"\r" in payload or b"\0" in payload:
        raise ValueError("noncanonical private Yabause FAD log")
    lines = payload.splitlines()
    if not lines or any(not FAD.fullmatch(line) for line in lines):
        raise ValueError("private disc logger contains nonnumeric entries")
    return len(lines), hashlib.sha256(payload).digest()


def _capture(directory: Path, expected_pad: bytes) -> dict:
    _private_directory(directory)
    if _private_regular(directory / "pad-events.txt", 512) != expected_pad:
        raise ValueError("Saturn START pulse missing or out of frame")
    fad_count, fad_hash = _count_canonical_fads(directory)
    screenshot = _private_regular(directory / f"frame-{FRAME_COUNT}.png", MAX_PNG_BYTES)
    dims = validate_png_file(screenshot)
    if dims[0] < 64 or dims[1] < 64:
        raise ValueError("invalid original Saturn framebuffer dimensions")
    final_png_hash = hashlib.sha256(screenshot).digest()
    return {
        "fad_count": fad_count,
        "fad_hash": fad_hash,
        "final_png_hash": final_png_hash,
        "dimensions": dims,
    }


def audit_start_ab(control: Path, intervention: Path) -> dict:
    if (not isinstance(control, Path) or not isinstance(intervention, Path) or
            not control.is_absolute() or not intervention.is_absolute() or
            control.resolve() == intervention.resolve()):
        raise ValueError("two distinct absolute private A/B workspaces required")
    before = _capture(control, CONTROL)
    after = _capture(intervention, START)
    if before["dimensions"] != after["dimensions"]:
        raise ValueError("A/B final framebuffer geometry must match")
    return {
        "schema_version": 1,
        "kind": "STAGE107_PRIVATE_SATURN_START_AB_FILE_INTEGRITY_ONLY",
        "same_13200_frame_window_claimed_by_private_pad_receipts": True,
        "control_pad_connected_no_input": True,
        "intervention_start_press_frame": PRESS_AT,
        "intervention_start_release_frame": RELEASE_AT,
        "control_fad_events": before["fad_count"],
        "intervention_fad_events": after["fad_count"],
        "numeric_cd_logs_differ": before["fad_hash"] != after["fad_hash"],
        "final_png_files_differ": before["final_png_hash"] != after["final_png_hash"],
        "final_png_dimensions_match": True,
        "actual_controller_pulse_independently_verified_in_emulator": False,
        "menu_content_visually_identified": False,
        "first_battle_visually_identified": False,
        "original_gameplay_frame_to_cd_causality_verified": False,
        "private_files_or_hashes_exported": False,
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--control",type=Path,required=True)
    p.add_argument("--start",type=Path,required=True)
    a=p.parse_args()
    try:
        report=audit_start_ab(a.control,a.start)
    except (OSError,ValueError,TypeError):
        print("STAGE107_PRIVATE_START_AB_REJECTED",file=sys.stderr)
        return 1
    print(json.dumps(report,sort_keys=True))
    return 0


if __name__=="__main__":
    sys.exit(main())
