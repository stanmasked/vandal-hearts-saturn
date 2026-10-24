#!/usr/bin/env python3
"""Stage147 four-control replay matrix, for the owner's private workstation.

This tool compares two *control* captures per pinned Yabause build. It does not
launch an emulator or independently prove that runs share a host, media image,
or runner identity. Never copy original screenshots or media to public CI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.saturn_private_capture_cohort import _private_directory, _private_regular
from tools.saturn_private_capture_session import _not_in_checkout
from tools.saturn_private_original_start_sequence import FRAME_STATS
from tools.saturn_private_frame_witness import validate_png_file
from tools.saturn_private_start_ab import MAX_PNG_BYTES
from tools.saturn_private_prologue_continue_eleventh_c_audit import (
    DECA_EVENTS_132, DECA_STATE_132,
)
from tools.saturn_private_prologue_continue_twelfth_c_audit import (
    CONTROL_EVENTS, CONTROL_STATE,
)
from tools import saturn_private_same_session_cross_build_prefix as prefix

LABELS = ("stage144_a", "stage144_b", "stage145_a", "stage145_b")
PAIR_INDEXES = ((0, 1), (2, 3), (0, 2), (0, 3), (1, 2), (1, 3))
FRAME_LIMITS = (132000, 132000, 144000, 144000)
PAD_RECEIPTS = (
    (DECA_EVENTS_132, DECA_STATE_132),
    (DECA_EVENTS_132, DECA_STATE_132),
    (CONTROL_EVENTS, CONTROL_STATE),
    (CONTROL_EVENTS, CONTROL_STATE),
)


def _validate_capture(path: Path, index: int) -> None:
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("Stage147 capture must be an absolute nonsymlinked private directory")
    _not_in_checkout(path)
    _private_directory(path)
    # Each control must be a complete, unmodified 132k/144k-frame capture.
    # A plausible final frames.stats alone must never authorize a partial run.
    expected_frames = {f"frame-{n}.png" for n in range(120, FRAME_LIMITS[index] + 1, 120)}
    expected_sidecars = {"pre.png", "post.png", "frames.stats", "fad.vhcdlog",
                         "pad-events.txt", "pad-state.txt", "sh2-window.txt", "video-state.txt"}
    if {p.name for p in path.iterdir()} != expected_frames | expected_sidecars:
        raise ValueError("Stage147 full-stage capture file set incomplete or unexpected")
    events, state = PAD_RECEIPTS[index]
    if _private_regular(path / "pad-events.txt", 4096) != events:
        raise ValueError("Stage147 control PAD event sequence differs from pinned stage")
    if _private_regular(path / "pad-state.txt", 4096) != state:
        raise ValueError("Stage147 control PAD state sequence differs from pinned stage")
    match = FRAME_STATS.fullmatch(_private_regular(path / "frames.stats", 256))
    if not match:
        raise ValueError("Stage147 frame statistics malformed")
    frames, pc_before, pc_after, width, height = map(int, match.groups())
    if (frames != FRAME_LIMITS[index] or pc_before > 0xFFFFFFFF or
            pc_after > 0xFFFFFFFF or not (64 <= width <= 704 and 64 <= height <= 512)):
        raise ValueError("Stage147 expected full-stage frame statistics invalid")
    pre = _private_regular(path / "pre.png", MAX_PNG_BYTES)
    post = _private_regular(path / "post.png", MAX_PNG_BYTES)
    validate_png_file(pre)
    if validate_png_file(post) != (width, height):
        raise ValueError("Stage147 final framebuffer dimensions mismatch")
    # Existing prefix audit decodes/checks all first 800 checkpoint PNGs.
    # Validate the remaining tail too, without exposing a frame or checksum.
    for frame in range(prefix.FRAME_END + prefix.FRAME_STEP,
                       FRAME_LIMITS[index] + 1, prefix.FRAME_STEP):
        raw = _private_regular(path / f"frame-{frame}.png", MAX_PNG_BYTES)
        if validate_png_file(raw) != (width, height):
            raise ValueError("Stage147 late framebuffer geometry mismatch")
    expected_diagnostics = {0} | set(range(120, FRAME_LIMITS[index] + 1, 120))
    for name, pattern in (("sh2-window.txt", prefix.SH2_LINE),
                          ("video-state.txt", prefix.VIDEO_LINE)):
        records = prefix._read_frame_diagnostics(path, name, pattern)
        if set(records) != expected_diagnostics:
            raise ValueError("Stage147 full-stage diagnostic sequence incomplete or unexpected")



def audit_private_stage147_replay_matrix(paths: tuple[Path, Path, Path, Path]) -> dict:
    if len(paths) != 4 or any(not isinstance(p, Path) for p in paths):
        raise ValueError("Stage147 requires four named capture directories")
    if len({p.resolve() for p in paths}) != 4:
        raise ValueError("Stage147 capture directories must be distinct")
    for index, path in enumerate(paths):
        _validate_capture(path, index)

    mismatches = {f"{LABELS[a]}__{LABELS[b]}": [] for a, b in PAIR_INDEXES}
    dimensions: list[tuple[int, int] | None] = [None] * 4
    stats_dimensions = []
    for path in paths:
        match = FRAME_STATS.fullmatch(_private_regular(path / "frames.stats", 256))
        stats_dimensions.append(tuple(map(int, match.groups()[-2:])))
    for frame in prefix.CHECKPOINTS:
        pixels = []
        for index, path in enumerate(paths):
            dims, rgb = prefix._read_rgb(path, frame, dimensions[index])
            dimensions[index] = dimensions[index] or dims
            if dims != stats_dimensions[index]:
                raise ValueError("Stage147 framebuffer differs from final frame statistics")
            pixels.append(rgb)
        if len(set(dimensions)) != 1:
            raise ValueError("Stage147 framebuffer dimensions differ between runs")
        for a, b in PAIR_INDEXES:
            if pixels[a] != pixels[b]:
                mismatches[f"{LABELS[a]}__{LABELS[b]}"].append(frame)

    sh2 = [prefix._read_frame_diagnostics(p, "sh2-window.txt", prefix.SH2_LINE) for p in paths]
    video = [prefix._read_frame_diagnostics(p, "video-state.txt", prefix.VIDEO_LINE) for p in paths]
    fad = [prefix._read_fad(p) for p in paths]

    comparison = {}
    for a, b in PAIR_INDEXES:
        key = f"{LABELS[a]}__{LABELS[b]}"
        drift = mismatches[key]
        fad_common = 0
        for line_a, line_b in zip(fad[a], fad[b]):
            if line_a != line_b:
                break
            fad_common += 1
        comparison[key] = {
            "pixel_mismatch_count": len(drift),
            "first_pixel_mismatch_frame": drift[0] if drift else None,
            "pixel_mismatch_ranges": prefix._mismatch_ranges(drift),
            "sh2_record_mismatch_count": sum(sh2[a][f] != sh2[b][f] for f in prefix.DIAGNOSTIC_FRAMES),
            "video_record_mismatch_count": sum(video[a][f] != video[b][f] for f in prefix.DIAGNOSTIC_FRAMES),
            "fad_common_prefix_record_count": fad_common,
            "fad_equal": fad[a] == fad[b],
        }

    a = comparison["stage144_a__stage144_b"]
    b = comparison["stage145_a__stage145_b"]
    within_pixel_equal = a["pixel_mismatch_count"] == 0 and b["pixel_mismatch_count"] == 0
    within_diagnostics_equal = all(
        obj["sh2_record_mismatch_count"] == 0 and
        obj["video_record_mismatch_count"] == 0 and obj["fad_equal"]
        for obj in (a, b)
    )
    repeatable = within_pixel_equal and within_diagnostics_equal
    cross_keys = ("stage144_a__stage145_a", "stage144_a__stage145_b",
                  "stage144_b__stage145_a", "stage144_b__stage145_b")
    cross_sets = [tuple(mismatches[key]) for key in cross_keys]
    cross_uniform = all(seq == cross_sets[0] for seq in cross_sets[1:])
    if not repeatable:
        classification = "within_build_replay_consistency_not_established"
    elif not cross_sets[0] and cross_uniform:
        classification = "decoded_prefix_and_within_build_diagnostics_aligned"
    elif cross_uniform:
        classification = "repeatable_cross_build_pixel_difference_candidate"
    else:
        classification = "cross_build_pixel_difference_not_reproducible"

    return {
        "schema": "vh-saturn-stage147-four-control-replay-matrix-1",
        "kind": "STAGE147_PRIVATE_CONTROL_REPLAY_MATRIX",
        "labels": list(LABELS),
        "checkpoint_count": len(prefix.CHECKPOINTS),
        "frame_start": prefix.FRAME_START,
        "frame_end": prefix.FRAME_END,
        "frame_step": prefix.FRAME_STEP,
        "comparisons": comparison,
        "within_build_pixels_equal": within_pixel_equal,
        "within_build_diagnostics_and_fad_equal": within_diagnostics_equal,
        "cross_build_mismatch_patterns_equal": cross_uniform,
        "classification": classification,
        "runner_sha256_independently_verified_by_this_tool": False,
        "same_host_and_disc_provenance_independently_verified": False,
        "caller_must_verify_full_paired_capture_audits_and_same_host_media": True,
        "source_level_causality_established": False,
        "original_media_or_frame_hashes_exported": False,
        "private_pixel_hashes_exported": False,
        "battle_or_tactical_player_control_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for label in LABELS:
        parser.add_argument("--" + label.replace("_", "-"), type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit_private_stage147_replay_matrix(tuple(getattr(args, x) for x in LABELS))
    except (OSError, ValueError, TypeError) as exc:
        print("STAGE147_PRIVATE_MATRIX_REJECTED", type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
