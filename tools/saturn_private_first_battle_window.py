#!/usr/bin/env python3
"""Stage115 private 48,000-frame paired run to verify the first tactical battle."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from tools.saturn_private_capture_cohort import _private_directory, _private_regular
from tools.saturn_private_capture_session import PINNED, _fingerprint, _not_in_checkout
from tools.saturn_private_frame_witness import validate_png_file
from tools.saturn_private_original_start_pair import _build_manifest, _check_media
from tools.saturn_private_original_start_sequence import (
    FIRST_PRESS, FIRST_RELEASE, MAX_SECONDS, SHA256, FRAME_STATS, SH2_LINE,
    VIDEO_LINE, _frame,
)
from tools.saturn_private_start_ab import _count_canonical_fads, MAX_PNG_BYTES

FRAME_COUNT = 48000
CONFIRM_PRESS = 12240
CONFIRM_RELEASE = 12246
CHECKPOINTS = tuple(range(120, FRAME_COUNT + 1, 120))
INITIAL_STATE = "VH_PADSTATE initial_start_bit=1\n"
FIRST_ONLY_EVENTS = (
    f"VH_PAD frame={FIRST_PRESS} button=START action=PRESS\n"
    f"VH_PAD frame={FIRST_RELEASE} button=START action=RELEASE\n"
    f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n"
).encode("ascii")
FIRST_ONLY_STATE = (
    INITIAL_STATE
    + f"VH_PADSTATE frame={FIRST_PRESS} start_bit=0\n"
    + f"VH_PADSTATE frame={FIRST_RELEASE} start_bit=1\n"
    + f"VH_PADSTATE mode=1 completed_frames={FRAME_COUNT}\n"
).encode("ascii")
CONFIRM_EVENTS = (
    f"VH_PAD frame={FIRST_PRESS} button=START action=PRESS\n"
    f"VH_PAD frame={FIRST_RELEASE} button=START action=RELEASE\n"
    f"VH_PAD frame={CONFIRM_PRESS} button=C action=PRESS\n"
    f"VH_PAD frame={CONFIRM_RELEASE} button=C action=RELEASE\n"
    f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n"
).encode("ascii")
CONFIRM_STATE = (
    INITIAL_STATE
    + "VH_PADSTATE initial_confirm_button=C active_low_bit=1\n"
    + f"VH_PADSTATE frame={FIRST_PRESS} start_bit=0\n"
    + f"VH_PADSTATE frame={FIRST_RELEASE} start_bit=1\n"
    + f"VH_PADSTATE frame={CONFIRM_PRESS} button=C active_low_bit=0\n"
    + f"VH_PADSTATE frame={CONFIRM_RELEASE} button=C active_low_bit=1\n"
    + f"VH_PADSTATE mode=1 completed_frames={FRAME_COUNT}\n"
).encode("ascii")
PRE_FIRST_CHECKPOINTS = tuple(range(120, FIRST_PRESS, 120))
PRE_CONFIRM_CHECKPOINTS = tuple(range(120, 12120 + 1, 120))
PRE_ATTRACT_DIVERGENCE_CHECKPOINTS = tuple(range(12360, 13680, 120))
POST_CONFIRM_CHECKPOINTS = tuple(range(12360, FRAME_COUNT + 1, 120))


def _fresh_dir(path: Path) -> None:
    _private_directory(path)
    if any(path.iterdir()):
        raise ValueError("Stage115 output directories must be fresh and empty")


def _check_long_frames(directory: Path) -> tuple[int, tuple[int, int]]:
    expected_pngs = {f"frame-{n}.png" for n in CHECKPOINTS}
    expected_files = expected_pngs | {
        "pre.png", "post.png", "frames.stats", "fad.vhcdlog",
        "pad-events.txt", "pad-state.txt", "sh2-window.txt", "video-state.txt",
    }
    actual_files = {p.name for p in directory.iterdir()}
    if actual_files != expected_files:
        raise ValueError("Stage115 checkpoint/output file set mismatch")

    dimensions = None
    for frame in CHECKPOINTS:
        dims, _ = _frame(directory, frame)
        if dimensions is None:
            dimensions = dims
        elif dims != dimensions:
            raise ValueError("Stage115 checkpoint dimensions changed")
    if dimensions is None:
        raise ValueError("Stage115 checkpoints missing")

    pre_dims = validate_png_file(_private_regular(directory / "pre.png", MAX_PNG_BYTES))
    post_dims = validate_png_file(_private_regular(directory / "post.png", MAX_PNG_BYTES))
    if pre_dims != dimensions or post_dims != dimensions:
        raise ValueError("Stage115 pre/post framebuffer dimensions differ")

    stats = _private_regular(directory / "frames.stats", 2048)
    match = FRAME_STATS.fullmatch(stats)
    if not match or int(match.group(1)) != FRAME_COUNT:
        raise ValueError("Stage115 frame statistics mismatch")
    if (int(match.group(4)), int(match.group(5))) != dimensions:
        raise ValueError("Stage115 frame-stat dimensions mismatch")

    expected_samples = [0] + list(CHECKPOINTS) + [FRAME_COUNT]
    for name, pattern in (("sh2-window.txt", SH2_LINE), ("video-state.txt", VIDEO_LINE)):
        raw = _private_regular(directory / name, 2 * 1024 * 1024)
        if not raw.endswith(b"\n") or b"\r" in raw or b"\x00" in raw:
            raise ValueError("Stage115 diagnostic log is not canonical")
        lines = raw.splitlines()
        if len(lines) != len(expected_samples):
            raise ValueError("Stage115 diagnostic sample count mismatch")
        observed = []
        for line in lines:
            parsed = pattern.fullmatch(line)
            if not parsed:
                raise ValueError("Stage115 diagnostic line malformed")
            observed.append(int(parsed.group(1)))
        if observed != expected_samples:
            raise ValueError("Stage115 diagnostic sequence mismatch")

    _count_canonical_fads(directory)
    return len(CHECKPOINTS), dimensions


def _equal_frame(a: Path, b: Path, frame: int) -> bool:
    a_dims, a_hash = _frame(a, frame)
    b_dims, b_hash = _frame(b, frame)
    if a_dims != b_dims:
        raise ValueError("Stage115 framebuffer geometries differ")
    return a_hash == b_hash


def audit_private_first_battle_window(first_only: Path, confirm_c: Path) -> dict:
    if not first_only.is_absolute() or not confirm_c.is_absolute():
        raise ValueError("absolute private Stage115 output paths required")
    if first_only.resolve() == confirm_c.resolve():
        raise ValueError("two distinct private Stage115 output directories required")
    _private_directory(first_only)
    _private_directory(confirm_c)
    if _private_regular(first_only / "pad-events.txt", 2048) != FIRST_ONLY_EVENTS:
        raise ValueError("Stage115 first-only controller receipt mismatch")
    if _private_regular(first_only / "pad-state.txt", 2048) != FIRST_ONLY_STATE:
        raise ValueError("Stage115 first-only active-low receipt mismatch")
    if _private_regular(confirm_c / "pad-events.txt", 2048) != CONFIRM_EVENTS:
        raise ValueError("Stage115 C-confirm controller receipt mismatch")
    if _private_regular(confirm_c / "pad-state.txt", 2048) != CONFIRM_STATE:
        raise ValueError("Stage115 C-confirm active-low receipt mismatch")

    first_count, first_dims = _check_long_frames(first_only)
    confirm_count, confirm_dims = _check_long_frames(confirm_c)
    if first_count != 400 or confirm_count != 400:
        raise ValueError("Stage115 checkpoint count mismatch")
    if first_dims != confirm_dims:
        raise ValueError("Stage115 final framebuffer geometries differ")

    for frame in PRE_FIRST_CHECKPOINTS:
        if not _equal_frame(first_only, confirm_c, frame):
            raise ValueError("Stage115 runs diverged before the first START pulse")
    for frame in PRE_CONFIRM_CHECKPOINTS:
        if not _equal_frame(first_only, confirm_c, frame):
            raise ValueError("Stage115 runs diverged before C confirm")

    early_changes = [
        frame for frame in PRE_ATTRACT_DIVERGENCE_CHECKPOINTS
        if not _equal_frame(first_only, confirm_c, frame)
    ]
    if not early_changes:
        raise ValueError("Stage115 C confirm had no early effect before the idle attract transition")

    post_equalities = {
        str(frame): _equal_frame(first_only, confirm_c, frame)
        for frame in POST_CONFIRM_CHECKPOINTS
    }
    first_cd, first_cd_hash = _count_canonical_fads(first_only)
    confirm_cd, confirm_cd_hash = _count_canonical_fads(confirm_c)
    return {
        "schema_version": 1,
        "kind": "STAGE115_PRIVATE_FIRST_BATTLE_WINDOW_INTEGRITY_ONLY",
        "frames_per_process": FRAME_COUNT,
        "independent_cold_boot_processes": 2,
        "checkpoint_png_count_per_process": 400,
        "all_checkpoint_pngs_valid_and_sequential": True,
        "private_frame_stats_and_diagnostic_sequences_verified": True,
        "same_dimensions_across_runs": True,
        "pre_first_start_checkpoints_compared": len(PRE_FIRST_CHECKPOINTS),
        "runs_identical_before_first_start": True,
        "first_only_and_confirm_identical_through_frame": max(PRE_CONFIRM_CHECKPOINTS),
        "first_c_confirm_divergence_before_idle_attract_transition": min(early_changes),
        "pre_attract_confirm_checkpoints_compared": len(PRE_ATTRACT_DIVERGENCE_CHECKPOINTS),
        "post_confirm_checkpoint_equalities": post_equalities,
        "frame_24000_differs_from_first_start_only_control": not post_equalities["24000"],
        "frame_48000_differs_from_first_start_only_control": not post_equalities["48000"],
        "first_only_cd_event_count": first_cd,
        "confirm_c_cd_event_count": confirm_cd,
        "cd_logs_differ": first_cd_hash != confirm_cd_hash,
        "first_battle_or_player_control_verified": False,
        "requires_private_visual_review_of_late_frames": True,
        "original_media_or_frame_hashes_exported": False,
    }


def _run_one(executable: Path, cue: Path, directory: Path, *, confirm: bool, seconds: int) -> None:
    env = {
        "HOME": str(directory),
        "TMPDIR": str(directory),
        "PATH": os.defpath,
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
        "VH_SATURN_CAPTURE_GATE": str(directory / "gate"),
        "VH_SATURN_FAD_LOG": str(directory / "fad.vhcdlog"),
        "VH_SATURN_PRIVATE_FRAMES_DIR": str(directory),
        "VH_SATURN_START_AT_FRAME": str(FIRST_PRESS),
    }
    if confirm:
        env["VH_SATURN_CONFIRM_AT_FRAME"] = str(CONFIRM_PRESS)
        env["VH_SATURN_CONFIRM_BUTTON"] = "C"
    process = subprocess.Popen(
        [str(executable), "vh-private-frame-boot", str(cue), str(FRAME_COUNT)],
        cwd=directory, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True, preexec_fn=lambda: os.umask(0o077),
    )
    try:
        status = process.wait(timeout=seconds)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise ValueError("private Stage115 Saturn run timed out") from exc
    if status != 0:
        raise ValueError("private Stage115 Yabause process failed")
    if (directory / "gate").exists() or (directory / "gate").is_symlink():
        raise ValueError("private Stage115 CD capture gate was not closed")


def run_private_first_battle_window(
    cue: Path, track1: Path, track2: Path, executable: Path,
    expected_runner_sha256: str, first_only: Path, confirm_c: Path,
    *, seconds: int = 7200, pins: dict = PINNED,
) -> dict:
    if not isinstance(expected_runner_sha256, str) or not SHA256.fullmatch(expected_runner_sha256):
        raise ValueError("independent lowercase SHA-256 of public runner required")
    if type(seconds) is not int or not (1 <= seconds <= MAX_SECONDS):
        raise ValueError("invalid bounded private process timeout")
    if not executable.is_absolute() or executable.is_symlink():
        raise ValueError("absolute nonsymlinked public Yabause executable required")
    _not_in_checkout(executable)
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError("public Yabause executable must be executable")
    if any(not path.is_absolute() for path in (cue, track1, track2)):
        raise ValueError("absolute private Saturn media paths required")
    manifest = _build_manifest(cue, track1, track2)
    outputs = (first_only, confirm_c)
    if any(not path.is_absolute() for path in outputs):
        raise ValueError("absolute private Stage115 output paths required")
    if first_only.resolve() == confirm_c.resolve():
        raise ValueError("two distinct private Stage115 output directories required")
    for directory in outputs:
        _private_directory(directory)
        if any(directory.iterdir()):
            raise ValueError("Stage115 output directories must be fresh and empty")
    sources = {cue.resolve(), track1.resolve(), track2.resolve(), executable.resolve()}
    for directory in (first_only.resolve(), confirm_c.resolve()):
        if directory in sources or any(path in directory.parents for path in sources):
            raise ValueError("private output directory overlaps a source parent")
        if any(directory in path.parents for path in sources):
            raise ValueError("private output directory contains a source")
    initial_media = _check_media(manifest, pins)
    initial_runner = _fingerprint(executable)
    if initial_runner[1] != expected_runner_sha256:
        raise ValueError("public Yabause executable did not match independent SHA-256")

    for target, confirm in ((first_only, False), (confirm_c, True)):
        try:
            _run_one(executable, cue, target, confirm=confirm, seconds=seconds)
        finally:
            try:
                if _check_media(manifest, pins) != initial_media:
                    raise ValueError("original Saturn source changed during Stage115")
            except (OSError, ValueError) as exc:
                raise ValueError("original Saturn source changed during Stage115") from exc
            if _fingerprint(executable) != initial_runner:
                raise ValueError("public Yabause executable changed during Stage115")
    report = audit_private_first_battle_window(first_only, confirm_c)
    report.update({
        "same_pinned_original_media_before_and_after_both_processes": True,
        "same_public_runner_file_identity_and_digest_before_and_after": True,
        "both_private_processes_returned_zero_status": True,
        "private_environment_allowlisted": True,
        "original_first_battle_claimed": False,
    })
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("cue", "track1", "track2", "executable", "first-only", "confirm-c"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--timeout", type=int, default=7200)
    args = parser.parse_args()
    try:
        report = run_private_first_battle_window(
            args.cue, args.track1, args.track2, args.executable,
            args.expected_runner_sha256, args.first_only, args.confirm_c,
            seconds=args.timeout,
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        print("STAGE115_PRIVATE_BATTLE_WINDOW_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
