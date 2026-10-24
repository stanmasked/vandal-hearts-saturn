#!/usr/bin/env python3
"""Stage143 full paired 120,000-frame capture audit; private bytes stay local.

The command combines the existing strict PAD/CD/diagnostic receipt audit with a
full PNG-content pass. It prints only counts and frame indices, never image
bytes, screenshot hashes, raw traces, or local paths. It does not claim battle
control merely because the intervention changed the framebuffer.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

from tools.saturn_private_prologue_continue_tenth_c import (
    CONFIRM10_PRESS, FRAME_COUNT, PRE_TENTH_CHECKPOINTS,
    audit_private_prologue_continue_tenth_c,
)
from tools.saturn_stage143_visual_witness_gate import (
    MAX_PNG_BYTES, _black_runs, _decode_is_black,
)

STEP = 120
CHECKPOINTS = tuple(range(STEP, FRAME_COUNT + 1, STEP))
FRAME_RE = re.compile(r"frame-(\d+)\.png\Z")
REVIEWED_BLACK_RUNS = (
    (1560, 1560), (11640, 11880), (12360, 12360),
    (22560, 22800), (48840, 49080), (50640, 50640), (60120, 60120),
)


def _outside_checkout(path: Path) -> None:
    resolved = path.resolve()
    for candidate in (path, resolved):
        for parent in (candidate, *candidate.parents):
            if (parent / ".git").exists():
                raise ValueError("private audit data must remain outside Git checkout")


def _safe_directory(path: Path) -> None:
    _outside_checkout(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ValueError("absolute private nonsymlinked capture directory required")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("private capture directory permissions are too broad")


def audit_visual_checkpoint_pair(control: Path, enabled: Path, *, through_frame: int,
                                 reviewed_black_runs: tuple[tuple[int, int], ...] = ()) -> dict:
    """Decode a bounded checkpoint pair; short windows are for synthetic CI tests."""
    if type(through_frame) is not int or through_frame < STEP * 2 or through_frame % STEP:
        raise ValueError("invalid checkpoint window")
    _safe_directory(control)
    _safe_directory(enabled)
    if (control.resolve() == enabled.resolve()
            or control.resolve() in enabled.resolve().parents
            or enabled.resolve() in control.resolve().parents):
        raise ValueError("capture cohorts must be separate directories")
    frames = tuple(range(STEP, through_frame + 1, STEP))
    reviewed = []
    for item in reviewed_black_runs:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError("reviewed span must be a start/end pair")
        first, last = item
        if (type(first) is not int or type(last) is not int or first < STEP
                or first > last or last > through_frame or first % STEP or last % STEP):
            raise ValueError("reviewed span is outside checkpoint window")
        reviewed.append((first, last))
    reviewed.sort()
    if len(set(reviewed)) != len(reviewed) or any(
        reviewed[i][1] >= reviewed[i + 1][0] for i in range(len(reviewed) - 1)
    ):
        raise ValueError("reviewed spans duplicate or overlap")

    masks, equal_frames, different_frames = [], [], []
    for folder in (control, enabled):
        entries = tuple(folder.iterdir())
        if any(p.name.startswith("frame-") and not FRAME_RE.fullmatch(p.name) for p in entries):
            raise ValueError("malformed checkpoint filename")
        expected = {f"frame-{frame}.png" for frame in frames}
        actual = {p.name for p in entries if FRAME_RE.fullmatch(p.name)}
        if actual != expected:
            raise ValueError("checkpoint PNG sequence missing, duplicated, or unexpected")
        black = []
        for frame in frames:
            path = folder / f"frame-{frame}.png"
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                    or info.st_size < 33 or info.st_size > MAX_PNG_BYTES):
                raise ValueError("checkpoint PNG is unsafe or outside size bounds")
            black.append(_decode_is_black(path.read_bytes()))
        masks.append(tuple(black))

    # Compare bytes in a separate pass; hashes are intentionally never exported.
    for frame in frames:
        a, b = control / f"frame-{frame}.png", enabled / f"frame-{frame}.png"
        (equal_frames if a.read_bytes() == b.read_bytes() else different_frames).append(frame)
    mask_a, mask_b = masks
    runs_a, runs_b = _black_runs(frames, mask_a), _black_runs(frames, mask_b)
    ranges_a = tuple((r["first_frame"], r["last_frame"]) for r in runs_a)
    ranges_b = tuple((r["first_frame"], r["last_frame"]) for r in runs_b)
    reviewed_match = ranges_a == ranges_b and tuple(reviewed) == ranges_a
    mask_equal = mask_a == mask_b
    visual_accepted = bool(mask_equal and any(not x for x in mask_a)
                           and any(not x for x in mask_b) and reviewed_match)
    return {
        "schema": "vh-saturn-stage143-full-pair-visual-audit-1",
        "through_frame": through_frame,
        "checkpoint_pairs_decoded": len(frames),
        "control_black_checkpoint_count": sum(mask_a),
        "enabled_black_checkpoint_count": sum(mask_b),
        "control_black_prefix_count": next((i for i, x in enumerate(mask_a) if not x), len(frames)),
        "enabled_black_prefix_count": next((i for i, x in enumerate(mask_b) if not x), len(frames)),
        "control_black_runs": runs_a,
        "enabled_black_runs": runs_b,
        "reviewed_black_runs": [{"first_frame": x, "last_frame": y} for x, y in reviewed],
        "reviewed_black_runs_match_both_cohorts": reviewed_match,
        "black_classification_masks_match": mask_equal,
        "byte_identical_checkpoint_pair_count": len(equal_frames),
        "byte_different_checkpoint_pair_count": len(different_frames),
        "first_byte_different_frame": min(different_frames) if different_frames else None,
        "byte_equal_frames_before_tenth_c": sum(f < CONFIRM10_PRESS for f in equal_frames),
        "checkpoint_at_tenth_c_press_frame_equal": (
            CONFIRM10_PRESS in equal_frames if through_frame >= CONFIRM10_PRESS else None
        ),
        "byte_different_frames_after_tenth_c": sum(f > CONFIRM10_PRESS for f in different_frames),
        "visual_witness_accepted": visual_accepted,
        "raw_frame_hashes_exported": False,
    }


def audit_full_stage143_pair(control: Path, enabled: Path, controller_report_path: Path) -> dict:
    """Verify the completed private run, PAD receipts, and all 1,000 PNG pairs."""
    _safe_directory(control)
    _safe_directory(enabled)
    _outside_checkout(controller_report_path)
    if not controller_report_path.is_absolute() or controller_report_path.is_symlink():
        raise ValueError("absolute private controller report required")
    info = controller_report_path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 65536:
        raise ValueError("controller report unsafe")
    try:
        controller = json.loads(controller_report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("controller report unreadable") from exc
    required = {
        "frames_per_process": FRAME_COUNT,
        "checkpoint_png_count_per_process": len(CHECKPOINTS),
        "paired_cold_boot_processes": 2,
        "both_private_processes_returned_zero_status": True,
        "same_pinned_original_media_before_and_after_both_processes": True,
        "same_public_runner_file_identity_and_digest_before_and_after": True,
        "private_environment_allowlisted": True,
        "first_post_tenth_framebuffer_divergence_through_120000": 108120,
        "first_battle_claimed": False,
    }
    for key, expected in required.items():
        if controller.get(key) != expected:
            raise ValueError("controller report failed required integrity field")
    integrity = audit_private_prologue_continue_tenth_c(control, enabled)
    if (integrity.get("frames_per_process") != FRAME_COUNT
            or integrity.get("checkpoint_png_count_per_process") != len(CHECKPOINTS)
            or integrity.get("pre_tenth_checkpoint_equal_count") != len(PRE_TENTH_CHECKPOINTS)
            or integrity.get("first_post_tenth_framebuffer_divergence_through_120000") != 108120
            or integrity.get("first_battle_or_player_control_verified") is not False):
        raise ValueError("existing Stage125 paired integrity audit incomplete")
    visual = audit_visual_checkpoint_pair(
        control, enabled, through_frame=FRAME_COUNT, reviewed_black_runs=REVIEWED_BLACK_RUNS,
    )
    if (visual.get("checkpoint_pairs_decoded") != 1000
            or visual.get("byte_identical_checkpoint_pair_count") != 900
            or visual.get("byte_equal_frames_before_tenth_c") != 899
            or visual.get("checkpoint_at_tenth_c_press_frame_equal") is not True
            or visual.get("byte_different_checkpoint_pair_count") != 100
            or visual.get("byte_different_frames_after_tenth_c") != 100
            or visual.get("first_byte_different_frame") != 108120
            or visual.get("control_black_checkpoint_count") != 15
            or visual.get("enabled_black_checkpoint_count") != 15
            or visual.get("black_classification_masks_match") is not True
            or visual.get("visual_witness_accepted") is not True):
        raise ValueError("full Stage143 visual pair audit failed closed")
    return {
        "schema": "vh-saturn-stage143-full-pair-audit-1",
        "stage": 143,
        "kind": "STAGE143_FULL_PRIVATE_PAIR_AUDIT",
        "frames_per_process": FRAME_COUNT,
        "paired_cold_boot_processes": 2,
        "checkpoint_png_count_per_process": len(CHECKPOINTS),
        "all_pngs_decoded_and_crc_validated": True,
        "all_pad_receipts_and_diagnostic_sequences_verified": True,
        "source_media_and_runner_unchanged_per_controller_receipt": True,
        "pre_tenth_checkpoint_pairs_identical": 899,
        "press_frame_checkpoint_108000_identical": True,
        "post_tenth_checkpoint_pairs_different": 100,
        "first_post_tenth_framebuffer_divergence": 108120,
        "black_classification_masks_match": True,
        "black_checkpoint_count_per_cohort": 15,
        "black_boot_prefix_count_per_cohort": 2,
        "reviewed_internal_black_spans": [
            {"first_frame": x, "last_frame": y} for x, y in REVIEWED_BLACK_RUNS
        ],
        "all_internal_black_spans_reviewed_and_matching": True,
        "tenth_c_effect_on_original_framebuffer_confirmed": True,
        "original_gameplay_or_battle_verified": False,
        "first_battle_or_player_control_verified": False,
        "original_media_or_frame_hashes_exported": False,
        "raw_capture_archive_created_separately": True,
        "visual_gate": visual,
        "integrity_gate": integrity,
    }


def _write_report(path: Path, report: dict) -> None:
    if not path.is_absolute() or path.is_symlink() or path.exists():
        raise ValueError("report destination must be new, absolute, and nonsymlinked")
    _outside_checkout(path)
    payload = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--enabled", type=Path, required=True)
    parser.add_argument("--controller-report", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit_full_stage143_pair(args.control, args.enabled, args.controller_report)
        _write_report(args.report_out, report)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        print("STAGE143_FULL_PAIR_AUDIT_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps({k: v for k, v in report.items() if k not in ("visual_gate", "integrity_gate")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
