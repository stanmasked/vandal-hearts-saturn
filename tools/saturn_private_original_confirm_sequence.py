#!/usr/bin/env python3
"""Stage114 private A/C confirm experiment; original media and captures stay local."""
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
from tools.saturn_private_original_start_pair import _build_manifest, _check_media
from tools.saturn_private_original_start_sequence import (
    FIRST_PRESS, FIRST_RELEASE, FRAME_COUNT, MAX_SECONDS, SHA256,
    _check_frames, _count_canonical_fads, _frame,
)

CONFIRM_PRESS = 12240
CONFIRM_RELEASE = 12246
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
PRE_FIRST_CHECKPOINTS = tuple(range(120, FIRST_PRESS, 120))
PRE_CONFIRM_CHECKPOINTS = tuple(range(120, 12120 + 1, 120))
PRE_ATTRACT_DIVERGENCE_CHECKPOINTS = tuple(range(12360, 13680, 120))
POST_CONFIRM_CHECKPOINTS = tuple(range(12360, FRAME_COUNT + 1, 120))


def _confirm_events(button: str) -> bytes:
    return (
        f"VH_PAD frame={FIRST_PRESS} button=START action=PRESS\n"
        f"VH_PAD frame={FIRST_RELEASE} button=START action=RELEASE\n"
        f"VH_PAD frame={CONFIRM_PRESS} button={button} action=PRESS\n"
        f"VH_PAD frame={CONFIRM_RELEASE} button={button} action=RELEASE\n"
        f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n"
    ).encode("ascii")


def _confirm_state(button: str) -> bytes:
    return (
        INITIAL_STATE
        + f"VH_PADSTATE initial_confirm_button={button} active_low_bit=1\n"
        + f"VH_PADSTATE frame={FIRST_PRESS} start_bit=0\n"
        + f"VH_PADSTATE frame={FIRST_RELEASE} start_bit=1\n"
        + f"VH_PADSTATE frame={CONFIRM_PRESS} button={button} active_low_bit=0\n"
        + f"VH_PADSTATE frame={CONFIRM_RELEASE} button={button} active_low_bit=1\n"
        + f"VH_PADSTATE mode=1 completed_frames={FRAME_COUNT}\n"
    ).encode("ascii")


def _fresh_dir(path: Path) -> None:
    _private_directory(path)
    if any(path.iterdir()):
        raise ValueError("Stage114 output directories must be fresh and empty")


def _run_one(
    executable: Path,
    cue: Path,
    directory: Path,
    *,
    confirm_button: str | None,
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
        "VH_SATURN_START_AT_FRAME": str(FIRST_PRESS),
    }
    if confirm_button is not None:
        env["VH_SATURN_CONFIRM_AT_FRAME"] = str(CONFIRM_PRESS)
        env["VH_SATURN_CONFIRM_BUTTON"] = confirm_button

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
        raise ValueError("private Stage114 Saturn run timed out") from exc
    if status != 0:
        raise ValueError("private Stage114 Yabause process failed")
    if (directory / "gate").exists() or (directory / "gate").is_symlink():
        raise ValueError("private Stage114 CD capture gate was not closed")


def _equal_frame(a: Path, b: Path, frame: int) -> bool:
    a_dims, a_hash = _frame(a, frame)
    b_dims, b_hash = _frame(b, frame)
    if a_dims != b_dims:
        raise ValueError("Stage114 framebuffer geometries differ")
    return a_hash == b_hash


def audit_private_confirm_sequence(first_only: Path, confirm: Path, button: str) -> dict:
    if button not in ("A", "C"):
        raise ValueError("Stage114 confirm button must be A or C")
    if not first_only.is_absolute() or not confirm.is_absolute():
        raise ValueError("absolute private Stage114 output paths required")
    if first_only.resolve() == confirm.resolve():
        raise ValueError("two distinct private Stage114 output directories required")
    _private_directory(first_only)
    _private_directory(confirm)

    if _private_regular(first_only / "pad-events.txt", 2048) != FIRST_ONLY_EVENTS:
        raise ValueError("Stage114 first-only controller receipt mismatch")
    if _private_regular(first_only / "pad-state.txt", 2048) != FIRST_ONLY_STATE:
        raise ValueError("Stage114 first-only active-low receipt mismatch")
    if _private_regular(confirm / "pad-events.txt", 2048) != _confirm_events(button):
        raise ValueError("Stage114 confirm controller receipt mismatch")
    if _private_regular(confirm / "pad-state.txt", 2048) != _confirm_state(button):
        raise ValueError("Stage114 confirm active-low receipt mismatch")

    first_count, first_dims = _check_frames(first_only)
    confirm_count, confirm_dims = _check_frames(confirm)
    if first_count != FRAME_COUNT // 120 or confirm_count != FRAME_COUNT // 120:
        raise ValueError("Stage114 checkpoint count mismatch")
    if first_dims != confirm_dims:
        raise ValueError("Stage114 final framebuffer geometries differ")

    for frame in PRE_FIRST_CHECKPOINTS:
        if not _equal_frame(first_only, confirm, frame):
            raise ValueError("Stage114 runs diverged before the first START pulse")
    for frame in PRE_CONFIRM_CHECKPOINTS:
        if not _equal_frame(first_only, confirm, frame):
            raise ValueError("Stage114 runs diverged before the A/C confirm pulse")

    early_equalities = {
        str(frame): _equal_frame(first_only, confirm, frame)
        for frame in PRE_ATTRACT_DIVERGENCE_CHECKPOINTS
    }
    early_changes = [
        frame for frame in PRE_ATTRACT_DIVERGENCE_CHECKPOINTS
        if not early_equalities[str(frame)]
    ]
    if not early_changes:
        raise ValueError(
            "Stage114 confirm produced no framebuffer divergence before the idle attract transition"
        )

    post_equalities = {
        str(frame): _equal_frame(first_only, confirm, frame)
        for frame in POST_CONFIRM_CHECKPOINTS
    }
    cd_first, cd_first_hash = _count_canonical_fads(first_only)
    cd_confirm, cd_confirm_hash = _count_canonical_fads(confirm)

    return {
        "schema_version": 1,
        "kind": "STAGE114_PRIVATE_MENU_CONFIRM_INTEGRITY_ONLY",
        "confirm_button": button,
        "frames_per_process": FRAME_COUNT,
        "independent_cold_boot_processes": 2,
        "checkpoint_png_count_per_process": FRAME_COUNT // 120,
        "all_checkpoint_pngs_valid_and_sequential": True,
        "private_frame_stats_verified": True,
        "same_dimensions_across_runs": True,
        "pre_first_start_checkpoints_compared": len(PRE_FIRST_CHECKPOINTS),
        "runs_identical_before_first_start": True,
        "first_only_and_confirm_identical_through_frame": max(PRE_CONFIRM_CHECKPOINTS),
        "confirm_first_divergence_before_idle_attract_transition": min(early_changes),
        "pre_attract_confirm_checkpoints_compared": len(PRE_ATTRACT_DIVERGENCE_CHECKPOINTS),
        "post_confirm_checkpoint_equalities": post_equalities,
        "first_only_cd_event_count": cd_first,
        "confirm_cd_event_count": cd_confirm,
        "cd_logs_differ": cd_first_hash != cd_confirm_hash,
        "new_game_or_first_battle_verified": False,
        "requires_private_visual_review_of_confirm_transition": True,
        "original_media_or_frame_hashes_exported": False,
    }


def run_private_confirm_sequence(
    cue: Path,
    track1: Path,
    track2: Path,
    executable: Path,
    expected_runner_sha256: str,
    first_only: Path,
    confirm: Path,
    button: str,
    *,
    seconds: int = 7200,
    pins: dict = PINNED,
) -> dict:
    if button not in ("A", "C"):
        raise ValueError("Stage114 confirm button must be A or C")
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
    outputs = (first_only, confirm)
    if any(not path.is_absolute() for path in outputs):
        raise ValueError("absolute private Stage114 output paths required")
    if first_only.resolve() == confirm.resolve():
        raise ValueError("two distinct private Stage114 output directories required")
    _fresh_dir(first_only)
    _fresh_dir(confirm)

    sources = {cue.resolve(), track1.resolve(), track2.resolve(), executable.resolve()}
    for directory in (first_only.resolve(), confirm.resolve()):
        if directory in sources or any(path in directory.parents for path in sources):
            raise ValueError("private output directory overlaps a source parent")
        if any(directory in path.parents for path in sources):
            raise ValueError("private output directory contains a source")

    initial_media = _check_media(manifest, pins)
    initial_runner = _fingerprint(executable)
    if initial_runner[1] != expected_runner_sha256:
        raise ValueError("public Yabause executable did not match independent SHA-256")

    for target, pulse in ((first_only, None), (confirm, button)):
        try:
            _run_one(executable, cue, target, confirm_button=pulse, seconds=seconds)
        finally:
            try:
                if _check_media(manifest, pins) != initial_media:
                    raise ValueError("original Saturn source changed during Stage114")
            except (OSError, ValueError) as exc:
                raise ValueError("original Saturn source changed during Stage114") from exc
            if _fingerprint(executable) != initial_runner:
                raise ValueError("public Yabause executable changed during Stage114")

    report = audit_private_confirm_sequence(first_only, confirm, button)
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
    for flag in ("cue", "track1", "track2", "executable", "first-only", "confirm"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--confirm-button", choices=("A", "C"), required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--timeout", type=int, default=7200)
    args = parser.parse_args()
    try:
        report = run_private_confirm_sequence(
            args.cue, args.track1, args.track2, args.executable,
            args.expected_runner_sha256, args.first_only, args.confirm,
            args.confirm_button, seconds=args.timeout,
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        print("STAGE114_PRIVATE_CONFIRM_RUN_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
