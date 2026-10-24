#!/usr/bin/env python3
"""Compare fresh Stage144 and Stage145 captures from the same private host.

Only aggregate pixel/diagnostic mismatch counts and checkpoint indices are
reported. The tool never exports screenshots, image hashes, original media,
or runner binaries.
"""
from __future__ import annotations

import argparse
from io import BytesIO
import json
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
CHECKPOINTS = tuple(range(FRAME_START, FRAME_END + 1, FRAME_STEP))
DIAGNOSTIC_FRAMES = (0,) + CHECKPOINTS
FRAME_NAME = re.compile(r"frame-(\d+)\.png\Z")
SH2_LINE = re.compile(r"VH_SH2 frame=(\d+) .+\Z")
VIDEO_LINE = re.compile(r"VH_VIDEO frame=(\d+) .+\Z")
FAD_LINE = re.compile(r"VHCD_FAD (0|[1-9][0-9]*)\Z")
MAX_DIAGNOSTIC_BYTES = 2 * 1024 * 1024


def _validate_frame_set(directory: Path) -> None:
    expected = {f"frame-{n}.png" for n in CHECKPOINTS}
    found = {p.name for p in directory.iterdir() if p.name.startswith("frame-") and p.suffix == ".png"}
    if not expected.issubset(found):
        raise ValueError("same-session cross-build checkpoint set incomplete")
    for name in found:
        match = FRAME_NAME.fullmatch(name)
        if not match or int(match.group(1)) < FRAME_STEP or int(match.group(1)) % FRAME_STEP:
            raise ValueError("same-session cross-build checkpoint filename is noncanonical")


def _read_rgb(directory: Path, frame: int, expected_dims: tuple[int, int] | None) -> tuple[tuple[int, int], bytes]:
    raw = _private_regular(directory / f"frame-{frame}.png", MAX_PNG_BYTES)
    dims = validate_png_file(raw)
    if not (64 <= dims[0] <= 704 and 64 <= dims[1] <= 512):
        raise ValueError("same-session cross-build PNG geometry outside allowed bounds")
    if expected_dims is not None and dims != expected_dims:
        raise ValueError("same-session cross-build framebuffer geometry changed within a run")
    try:
        with Image.open(BytesIO(raw)) as image:
            image.load()
            pixels = image.convert("RGB").tobytes()
    except Exception as exc:
        raise ValueError("same-session cross-build PNG could not be decoded") from exc
    if len(pixels) != dims[0] * dims[1] * 3:
        raise ValueError("same-session cross-build decoded pixel length mismatch")
    return dims, pixels


def _read_frame_diagnostics(directory: Path, filename: str, pattern: re.Pattern[str]) -> dict[int, str]:
    raw = _private_regular(directory / filename, MAX_DIAGNOSTIC_BYTES)
    if not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise ValueError("same-session cross-build diagnostic text is noncanonical")
    result: dict[int, str] = {}
    duplicate_terminal_seen = False
    frame_files = [
        int(match.group(1))
        for item in directory.iterdir()
        if (match := FRAME_NAME.fullmatch(item.name)) is not None
    ]
    if not frame_files:
        raise ValueError("same-session cross-build has no checkpoint files")
    terminal_frame = max(frame_files)
    for line in raw.decode("ascii").splitlines():
        match = pattern.fullmatch(line)
        if not match:
            raise ValueError("same-session cross-build diagnostic record malformed")
        frame = int(match.group(1))
        if frame in result:
            # Yabause records the final checkpoint once in the loop and once
            # during shutdown. Permit exactly one identical duplicate only
            # for the terminal frame beyond the compared prefix.
            if (frame == terminal_frame and frame > FRAME_END and
                    line == result[frame] and not duplicate_terminal_seen):
                duplicate_terminal_seen = True
                continue
            raise ValueError("same-session cross-build diagnostic frame duplicated")
        result[frame] = line
    if not set(DIAGNOSTIC_FRAMES).issubset(result):
        raise ValueError("same-session cross-build diagnostic samples incomplete")
    return result


def _read_fad(directory: Path) -> list[str]:
    raw = _private_regular(directory / "fad.vhcdlog", MAX_DIAGNOSTIC_BYTES)
    if not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise ValueError("same-session cross-build FAD log is noncanonical")
    lines = raw.decode("ascii").splitlines()
    if not lines or any(not FAD_LINE.fullmatch(line) for line in lines):
        raise ValueError("same-session cross-build FAD record malformed")
    return lines


def _mismatch_ranges(frames: list[int]) -> list[dict[str, int]]:
    ranges: list[list[int]] = []
    for frame in frames:
        if not ranges or frame > ranges[-1][-1] + FRAME_STEP:
            ranges.append([frame])
        else:
            ranges[-1].append(frame)
    return [{"start_frame": r[0], "end_frame": r[-1], "checkpoint_count": len(r)} for r in ranges]


def audit_private_same_session_cross_build_prefix(stage144: Path, stage145: Path) -> dict:
    paths = (stage144, stage145)
    if any(not p.is_absolute() or p.is_symlink() for p in paths):
        raise ValueError("same-session cross-build inputs must be absolute nonsymlinked private directories")
    if stage144.resolve() == stage145.resolve():
        raise ValueError("same-session cross-build audit requires two distinct run directories")
    for path in paths:
        _not_in_checkout(path)
        _private_directory(path)
        _validate_frame_set(path)

    dimensions: list[tuple[int, int] | None] = [None, None]
    pixel_mismatches: list[int] = []
    for frame in CHECKPOINTS:
        left_dims, left_pixels = _read_rgb(stage144, frame, dimensions[0])
        right_dims, right_pixels = _read_rgb(stage145, frame, dimensions[1])
        dimensions[0] = dimensions[0] or left_dims
        dimensions[1] = dimensions[1] or right_dims
        if left_dims != right_dims:
            raise ValueError("same-session cross-build framebuffer dimensions differ")
        if left_pixels != right_pixels:
            pixel_mismatches.append(frame)

    diagnostic_results = {}
    for key, filename, pattern in (
        ("sh2", "sh2-window.txt", SH2_LINE),
        ("video", "video-state.txt", VIDEO_LINE),
    ):
        left = _read_frame_diagnostics(stage144, filename, pattern)
        right = _read_frame_diagnostics(stage145, filename, pattern)
        mismatches = [frame for frame in DIAGNOSTIC_FRAMES if left[frame] != right[frame]]
        diagnostic_results[f"{key}_diagnostic_record_mismatch_count"] = len(mismatches)
        diagnostic_results[f"first_{key}_diagnostic_mismatch_frame"] = min(mismatches) if mismatches else None

    left_fad = _read_fad(stage144)
    right_fad = _read_fad(stage145)
    common = 0
    for a, b in zip(left_fad, right_fad):
        if a != b:
            break
        common += 1

    return {
        "schema": "vh-saturn-same-session-cross-build-prefix-1",
        "kind": "STAGE144_STAGE145_SAME_SESSION_PREFIX_COMPARISON",
        "reference_stage": 144,
        "candidate_stage": 145,
        "frame_start": FRAME_START,
        "frame_end": FRAME_END,
        "frame_step": FRAME_STEP,
        "checkpoint_count": len(CHECKPOINTS),
        "pixel_equal_count": len(CHECKPOINTS) - len(pixel_mismatches),
        "pixel_mismatch_count": len(pixel_mismatches),
        "first_pixel_mismatch_frame": min(pixel_mismatches) if pixel_mismatches else None,
        "last_pixel_mismatch_frame": max(pixel_mismatches) if pixel_mismatches else None,
        "pixel_mismatch_ranges": _mismatch_ranges(pixel_mismatches),
        **diagnostic_results,
        "stage144_fad_record_count": len(left_fad),
        "stage145_fad_record_count": len(right_fad),
        "fad_common_prefix_record_count": common,
        "fad_logs_match_through_shorter_log": common == min(len(left_fad), len(right_fad)),
        "original_media_or_frame_hashes_exported": False,
        "private_pixel_hashes_exported": False,
        "battle_or_tactical_player_control_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage144-reference", type=Path, required=True)
    parser.add_argument("--stage145-reference", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit_private_same_session_cross_build_prefix(args.stage144_reference, args.stage145_reference)
    except (OSError, ValueError, TypeError) as exc:
        print("STAGE144_145_SAME_SESSION_PREFIX_AUDIT_REJECTED", type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
