#!/usr/bin/env python3
"""Compare decoded private framebuffer pixels across Stage144/145 builds.

The report contains only aggregate mismatch counts and checkpoint indices; it
never exports screenshots, image hashes, original media, or emulator binaries.
"""
from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path
import re
import sys

from PIL import Image

from tools.saturn_private_capture_cohort import _private_directory, _private_regular
from tools.saturn_private_capture_session import _not_in_checkout
from tools.saturn_private_frame_witness import validate_png_file
from tools.saturn_private_start_ab import MAX_PNG_BYTES

FRAME_START = 120
FRAME_END = 96000
FRAME_STEP = 120
FRAME_NAME = re.compile(r"frame-(\d+)\.png\Z")
CHECKPOINTS = tuple(range(FRAME_START, FRAME_END + 1, FRAME_STEP))


def _read_rgb(directory: Path, frame: int, expected_dims: tuple[int, int] | None) -> tuple[tuple[int, int], bytes]:
    path = directory / f"frame-{frame}.png"
    raw = _private_regular(path, MAX_PNG_BYTES)
    dims = validate_png_file(raw)
    if not (64 <= dims[0] <= 704 and 64 <= dims[1] <= 512):
        raise ValueError("cross-stage PNG geometry outside allowed bounds")
    if expected_dims is not None and dims != expected_dims:
        raise ValueError("cross-stage framebuffer geometry changed within a cohort")
    try:
        with Image.open(BytesIO(raw)) as image:
            image.load()
            rgb = image.convert("RGB")
            pixels = rgb.tobytes()
    except Exception as exc:
        raise ValueError("cross-stage PNG could not be decoded to pixels") from exc
    if len(pixels) != dims[0] * dims[1] * 3:
        raise ValueError("cross-stage decoded pixel length mismatch")
    return dims, pixels


def _validate_frame_set(directory: Path) -> None:
    expected = {f"frame-{n}.png" for n in CHECKPOINTS}
    found = {p.name for p in directory.iterdir() if p.name.startswith("frame-") and p.suffix == ".png"}
    if not expected.issubset(found):
        raise ValueError("cross-stage checkpoint file set incomplete")
    for name in found:
        match = FRAME_NAME.fullmatch(name)
        if not match or int(match.group(1)) < FRAME_STEP or int(match.group(1)) % FRAME_STEP:
            raise ValueError("cross-stage checkpoint filename is noncanonical")


def audit_private_cross_stage_prefix_drift(
    stage144_reference: Path, stage145_control: Path, stage145_enabled: Path,
) -> dict:
    paths = (stage144_reference, stage145_control, stage145_enabled)
    if any(not p.is_absolute() or p.is_symlink() for p in paths):
        raise ValueError("cross-stage inputs must be absolute nonsymlinked private directories")
    resolved = [p.resolve() for p in paths]
    if len(set(resolved)) != 3:
        raise ValueError("cross-stage audit requires three distinct cohort directories")
    for path in paths:
        _not_in_checkout(path)
        _private_directory(path)
        _validate_frame_set(path)

    dims_by_dir: list[tuple[int, int] | None] = [None, None, None]
    stage145_equal = 0
    control_mismatches = []
    enabled_mismatches = []
    for frame in CHECKPOINTS:
        decoded = []
        for i, directory in enumerate(paths):
            dims, pixels = _read_rgb(directory, frame, dims_by_dir[i])
            if dims_by_dir[i] is None:
                dims_by_dir[i] = dims
            decoded.append((dims, pixels))
        if decoded[0][0] != decoded[1][0] or decoded[0][0] != decoded[2][0]:
            raise ValueError("cross-stage framebuffer dimensions differ")
        if decoded[1][1] == decoded[2][1]:
            stage145_equal += 1
        else:
            raise ValueError("Stage145 cohorts differ within the pre-input prefix")
        if decoded[0][1] != decoded[1][1]:
            control_mismatches.append(frame)
        if decoded[0][1] != decoded[2][1]:
            enabled_mismatches.append(frame)

    return {
        "schema": "vh-saturn-cross-stage-prefix-drift-1",
        "kind": "STAGE144_145_DECODED_PIXEL_PREFIX_COMPARISON",
        "reference_stage": 144,
        "candidate_stage": 145,
        "frame_start": FRAME_START,
        "frame_end": FRAME_END,
        "frame_step": FRAME_STEP,
        "checkpoint_count": len(CHECKPOINTS),
        "stage145_control_enabled_equal_checkpoint_count": stage145_equal,
        "control_vs_stage144_pixel_equal_count": len(CHECKPOINTS) - len(control_mismatches),
        "control_vs_stage144_pixel_mismatch_count": len(control_mismatches),
        "enabled_vs_stage144_pixel_equal_count": len(CHECKPOINTS) - len(enabled_mismatches),
        "enabled_vs_stage144_pixel_mismatch_count": len(enabled_mismatches),
        "stage145_cross_stage_mismatch_sets_equal": control_mismatches == enabled_mismatches,
        "first_cross_stage_pixel_mismatch_frame": min(control_mismatches) if control_mismatches else None,
        "last_cross_stage_pixel_mismatch_frame": max(control_mismatches) if control_mismatches else None,
        "original_media_or_frame_hashes_exported": False,
        "private_pixel_hashes_exported": False,
        "battle_or_tactical_player_control_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage144-reference", type=Path, required=True)
    parser.add_argument("--stage145-control", type=Path, required=True)
    parser.add_argument("--stage145-enabled", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit_private_cross_stage_prefix_drift(
            args.stage144_reference, args.stage145_control, args.stage145_enabled,
        )
    except (OSError, ValueError, TypeError) as exc:
        print("STAGE144_145_PREFIX_DRIFT_AUDIT_REJECTED", type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print(__import__("json").dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
