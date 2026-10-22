#!/usr/bin/env python3
"""Stage108: verify that two protected Saturn START runs agree before input.

This reads only private Stage107 files. It never exports PNG pixels, game
media, numeric CD addresses, screenshot hashes or file paths. Pixel-file
identity is a reproducibility check, not proof of game response.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from tools.saturn_private_capture_cohort import _private_regular
from tools.saturn_private_frame_witness import validate_png_file
from tools.saturn_private_start_ab import (
    MAX_PNG_BYTES, audit_start_ab,
)

PRE_INPUT_FRAMES = (11880, 12000)
POST_INPUT_FRAMES = (12120, 13200)


def _frame(directory: Path, number: int) -> tuple[tuple[int, int], bytes]:
    # The original Yabause loop emits a PNG every 120 completed frames.
    data = _private_regular(directory / f"frame-{number}.png", MAX_PNG_BYTES)
    dimensions = validate_png_file(data)
    if dimensions[0] < 64 or dimensions[1] < 64:
        raise ValueError("invalid framebuffer dimensions")
    return dimensions, hashlib.sha256(data).digest()


def audit_pre_start_equivalence(control: Path, intervention: Path) -> dict:
    # First enforce both the private file protections and Stage107's exact
    # 12060 PRESS / 12066 RELEASE receipt, without repeating its logic.
    report = audit_start_ab(control, intervention)
    comparisons = {}
    for number in PRE_INPUT_FRAMES + POST_INPUT_FRAMES:
        baseline_dimensions, baseline_digest = _frame(control, number)
        start_dimensions, start_digest = _frame(intervention, number)
        if baseline_dimensions != start_dimensions:
            raise ValueError("same-frame A/B framebuffer dimensions differ")
        comparisons[number] = baseline_digest == start_digest

    # A difference before any requested input makes post-START attribution
    # unreliable; reject that comparison rather than claiming game response.
    if any(not comparisons[n] for n in PRE_INPUT_FRAMES):
        raise ValueError("A/B framebuffers diverged before the START pulse")

    return {
        **report,
        "schema_version": 2,
        "kind": "STAGE108_PRIVATE_START_PREINPUT_EQUIVALENCE_ONLY",
        "pre_input_frames_compared": list(PRE_INPUT_FRAMES),
        "pre_input_png_files_byte_identical": True,
        "post_input_frames_compared": list(POST_INPUT_FRAMES),
        "post_input_12120_png_files_differ": not comparisons[12120],
        "post_input_13200_png_files_differ": not comparisons[13200],
        "pre_input_reproducibility_verified_from_local_pngs": True,
        "post_input_difference_proves_game_reacted": False,
        "game_menu_visually_confirmed_by_this_auditor": False,
        "original_game_data_or_frame_hashes_exported": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--start", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit_pre_start_equivalence(args.control, args.start)
    except (OSError, ValueError, TypeError):
        print("STAGE108_PRIVATE_START_BASELINE_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
