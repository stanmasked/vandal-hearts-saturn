#!/usr/bin/env python3
"""Stage109: strict private genuine-Saturn START padbit A/B receipt audit.

Checks the Stage107 control/pressed witnesses and Stage109's new active-low
pad-state file. A pad-bit transition is NOT proof the Saturn guest read it.
Original CD addresses, game pixels, paths and hashes are never returned.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.saturn_private_capture_cohort import _private_regular
from tools.saturn_private_start_ab import (
    FRAME_COUNT, PRESS_AT, RELEASE_AT, audit_start_ab,
)

INITIAL = "VH_PADSTATE initial_start_bit=1\n"
CLOSE = "VH_PADSTATE mode={mode} completed_frames={frames}\n"
CONTROL_STATE = (INITIAL + CLOSE.format(mode=0, frames=FRAME_COUNT)).encode("ascii")
PRESSED_STATE = (
    INITIAL +
    f"VH_PADSTATE frame={PRESS_AT} start_bit=0\n" +
    f"VH_PADSTATE frame={RELEASE_AT} start_bit=1\n" +
    CLOSE.format(mode=1, frames=FRAME_COUNT)
).encode("ascii")


def audit_native_padbit_ab(control: Path, pressed: Path) -> dict:
    report = audit_start_ab(control, pressed)
    if _private_regular(control / "pad-state.txt", 256) != CONTROL_STATE:
        raise ValueError("no-input Saturn pad bit state mismatch")
    if _private_regular(pressed / "pad-state.txt", 256) != PRESSED_STATE:
        raise ValueError("pressed Saturn pad bit state mismatch")
    return {
        **report,
        "schema_version": 2,
        "kind": "STAGE109_PRIVATE_SATURN_PADBIT_STATE_INTEGRITY_ONLY",
        "no_input_pad_start_bit_stayed_released": True,
        "start_press_seen_in_host_padbits_as_active_low_zero": True,
        "start_release_seen_in_host_padbits_as_high_one": True,
        "padbit_receipts_match_stage107_input_frame_indices": True,
        "actual_guest_smpc_read_verified": False,
        "actual_game_menu_transition_verified": False,
        "actual_first_battle_verified": False,
        "original_media_frames_or_hashes_exported": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--control", type=Path, required=True)
    p.add_argument("--start", type=Path, required=True)
    args = p.parse_args()
    try:
        report = audit_native_padbit_ab(args.control, args.start)
    except (OSError, ValueError, TypeError):
        print("STAGE109_PRIVATE_PADBIT_AUDIT_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
