#!/usr/bin/env python3
"""Stage113: isolate the second START response with a private three-run A/B/C."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from tools.saturn_private_capture_cohort import _private_directory, _private_regular
from tools.saturn_private_capture_session import PINNED, _fingerprint, _not_in_checkout
from tools.saturn_private_original_start_pair import _build_manifest, _check_media
from tools.saturn_private_original_start_sequence import (
    CONTROL_EVENTS, CONTROL_STATE, FIRST_PRESS, FIRST_RELEASE, FRAME_COUNT,
    MAX_SECONDS, SHA256, SECOND_PRESS, SECOND_RELEASE, START_EVENTS, START_STATE,
    _check_frames, _count_canonical_fads, _frame,
)

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
PRE_FIRST_START_CHECKPOINTS = tuple(range(120, FIRST_PRESS, 120))
PRE_SECOND_START_CHECKPOINTS = tuple(range(120, 12120 + 1, 120))
POST_SECOND_START_CHECKPOINTS = tuple(range(12360, FRAME_COUNT + 1, 120))


def _fresh_dir(path: Path) -> None:
    _private_directory(path)
    if any(path.iterdir()):
        raise ValueError("Stage113 run directories must be fresh and empty")


def _run_one(
    executable: Path,
    cue: Path,
    directory: Path,
    *,
    pulse_count: int,
    seconds: int,
) -> None:
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
    }
    if pulse_count >= 1:
        env["VH_SATURN_START_AT_FRAME"] = str(FIRST_PRESS)
    if pulse_count >= 2:
        env["VH_SATURN_START_AT_FRAME2"] = str(SECOND_PRESS)

    process = subprocess.Popen(
        [str(executable), "vh-private-frame-boot", str(cue), str(FRAME_COUNT)],
        cwd=directory,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        preexec_fn=lambda: os.umask(0o077),
    )
    try:
        status = process.wait(timeout=seconds)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise ValueError("private Stage113 Saturn run timed out") from exc
    if status != 0:
        raise ValueError("private Stage113 Yabause process failed")
    if (directory / "gate").exists() or (directory / "gate").is_symlink():
        raise ValueError("private Stage113 CD capture gate was not closed")


def _equal_frame(a: Path, b: Path, frame: int) -> bool:
    a_dims, a_hash = _frame(a, frame)
    b_dims, b_hash = _frame(b, frame)
    if a_dims != b_dims:
        raise ValueError("Stage113 A/B/C framebuffer geometries differ")
    return a_hash == b_hash


def audit_private_start_triple(
    no_input: Path, first_only: Path, dual_start: Path
) -> dict:
    folders = (no_input, first_only, dual_start)
    if any(not path.is_absolute() for path in folders):
        raise ValueError("absolute private Stage113 workspaces required")
    if len({path.resolve() for path in folders}) != 3:
        raise ValueError("three distinct private Stage113 workspaces required")
    for path in folders:
        _private_directory(path)

    expected_receipts = (
        (no_input, CONTROL_EVENTS, CONTROL_STATE, "control"),
        (first_only, FIRST_ONLY_EVENTS, FIRST_ONLY_STATE, "first-only"),
        (dual_start, START_EVENTS, START_STATE, "dual-start"),
    )
    for folder, events, state, label in expected_receipts:
        if _private_regular(folder / "pad-events.txt", 2048) != events:
            raise ValueError("Stage113 " + label + " controller receipt mismatch")
        if _private_regular(folder / "pad-state.txt", 2048) != state:
            raise ValueError("Stage113 " + label + " active-low receipt mismatch")

    counts_and_dims = [_check_frames(path) for path in folders]
    if any(count != FRAME_COUNT // 120 for count, _ in counts_and_dims):
        raise ValueError("Stage113 checkpoint count mismatch")
    dims = [geometry for _, geometry in counts_and_dims]
    if len(set(dims)) != 1:
        raise ValueError("Stage113 final framebuffer geometries differ")

    # All cold boots must be byte-identical through the last checkpoint before
    # the first START pulse. This validates the three-way control baseline.
    for frame in PRE_FIRST_START_CHECKPOINTS:
        if not (
            _equal_frame(no_input, first_only, frame)
            and _equal_frame(no_input, dual_start, frame)
        ):
            raise ValueError("Stage113 runs diverged before the first START pulse")

    # The first-only and dual-pulse runs differ only by the second pulse, so
    # every checkpoint through frame 12120 must remain byte-identical.
    for frame in PRE_SECOND_START_CHECKPOINTS:
        if not _equal_frame(first_only, dual_start, frame):
            raise ValueError("Stage113 runs diverged before the second START pulse")

    if _equal_frame(no_input, first_only, 12120):
        raise ValueError("Stage113 first START did not produce a visible menu-frame difference")
    if _equal_frame(no_input, first_only, 13200):
        raise ValueError("Stage113 first START menu difference did not persist to frame 13200")

    post_second_equalities = {
        str(frame): _equal_frame(first_only, dual_start, frame)
        for frame in POST_SECOND_START_CHECKPOINTS
    }
    changed_frames = [
        frame for frame in POST_SECOND_START_CHECKPOINTS
        if not post_second_equalities[str(frame)]
    ]
    if not changed_frames:
        raise ValueError("Stage113 second START produced no measurable post-input framebuffer difference")

    cd_counts = {}
    cd_hashes = {}
    for label, folder in (
        ("no_input", no_input),
        ("first_only", first_only),
        ("dual_start", dual_start),
    ):
        count, digest = _count_canonical_fads(folder)
        cd_counts[label] = count
        cd_hashes[label] = digest

    return {
        "schema_version": 1,
        "kind": "STAGE113_PRIVATE_TRIPLE_START_AB_INTEGRITY_ONLY",
        "frames_per_process": FRAME_COUNT,
        "independent_cold_boot_processes": 3,
        "checkpoint_png_count_per_process": FRAME_COUNT // 120,
        "all_checkpoint_pngs_valid_and_sequential": True,
        "private_frame_stats_verified": True,
        "same_dimensions_across_all_runs": True,
        "pre_first_start_checkpoints_compared": len(PRE_FIRST_START_CHECKPOINTS),
        "all_runs_identical_before_first_start": True,
        "first_only_and_dual_identical_through_frame": max(PRE_SECOND_START_CHECKPOINTS),
        "first_start_menu_difference_verified_at_12120_and_13200": True,
        "second_start_post_input_frames_compared": list(POST_SECOND_START_CHECKPOINTS),
        "second_start_first_measurable_frame_difference": min(changed_frames),
        "first_only_vs_dual_post_second_start_equalities": post_second_equalities,
        "cd_event_counts": cd_counts,
        "first_only_and_dual_cd_logs_differ": cd_hashes["first_only"] != cd_hashes["dual_start"],
        "first_tactical_battle_verified": False,
        "requires_private_visual_review_for_battlefield": True,
        "original_media_or_frame_hashes_exported": False,
    }


def run_private_start_triple(
    cue: Path,
    track1: Path,
    track2: Path,
    executable: Path,
    expected_runner_sha256: str,
    no_input: Path,
    first_only: Path,
    dual_start: Path,
    *,
    seconds: int = 7200,
    pins: dict = PINNED,
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
    outputs = (no_input, first_only, dual_start)
    if any(not path.is_absolute() for path in outputs):
        raise ValueError("absolute private Stage113 output paths required")
    if len({path.resolve() for path in outputs}) != 3:
        raise ValueError("three distinct private Stage113 output directories required")
    _fresh_dir(no_input)
    _fresh_dir(first_only)
    _fresh_dir(dual_start)

    sources = {cue.resolve(), track1.resolve(), track2.resolve(), executable.resolve()}
    for directory in (no_input.resolve(), first_only.resolve(), dual_start.resolve()):
        if directory in sources or any(path in directory.parents for path in sources):
            raise ValueError("private output directory overlaps a source parent")
        if any(directory in path.parents for path in sources):
            raise ValueError("private output directory contains a source")

    initial_media = _check_media(manifest, pins)
    initial_runner = _fingerprint(executable)
    if initial_runner[1] != expected_runner_sha256:
        raise ValueError("public Yabause executable did not match independent SHA-256")

    for target, pulse_count in ((no_input, 0), (first_only, 1), (dual_start, 2)):
        try:
            _run_one(
                executable, cue, target, pulse_count=pulse_count, seconds=seconds
            )
        finally:
            try:
                if _check_media(manifest, pins) != initial_media:
                    raise ValueError("original Saturn source changed during Stage113")
            except (OSError, ValueError) as exc:
                raise ValueError("original Saturn source changed during Stage113") from exc
            if _fingerprint(executable) != initial_runner:
                raise ValueError("public Yabause executable changed during Stage113")

    report = audit_private_start_triple(no_input, first_only, dual_start)
    report.update({
        "same_pinned_original_media_before_and_after_all_three_processes": True,
        "same_public_runner_file_identity_and_digest_before_and_after": True,
        "all_three_private_processes_returned_zero_status": True,
        "private_environment_allowlisted": True,
        "original_first_battle_claimed": False,
    })
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("cue", "track1", "track2", "executable", "no-input", "first-only", "dual-start"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--timeout", type=int, default=7200)
    args = parser.parse_args()
    try:
        report = run_private_start_triple(
            args.cue, args.track1, args.track2, args.executable,
            args.expected_runner_sha256, args.no_input, args.first_only,
            args.dual_start, seconds=args.timeout,
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        print("STAGE113_PRIVATE_TRIPLE_START_RUN_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
