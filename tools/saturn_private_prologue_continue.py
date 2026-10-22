#!/usr/bin/env python3
"""Stage116 private paired 48,000-frame test for one additional C dialogue press."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
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
    FIRST_PRESS, FIRST_RELEASE, MAX_SECONDS, SHA256,
)
from tools.saturn_private_start_ab import _count_canonical_fads
from tools.saturn_private_first_battle_window import (
    CHECKPOINTS, FRAME_COUNT, _check_long_frames, _equal_frame,
)

CONFIRM_PRESS = 12240
CONFIRM_RELEASE = 12246
CONFIRM2_PRESS = 31200
CONFIRM2_RELEASE = 31206
PRE_FIRST_CHECKPOINTS = tuple(range(120, FIRST_PRESS, 120))
PRE_FIRST_CONFIRM_CHECKPOINTS = tuple(range(120, 12120 + 1, 120))
PRE_SECOND_CHECKPOINTS = tuple(range(120, CONFIRM2_PRESS, 120))
POST_SECOND_CHECKPOINTS = tuple(range(CONFIRM2_PRESS + 120, FRAME_COUNT + 1, 120))
POST_SECOND_BY_36K_CHECKPOINTS = tuple(range(CONFIRM2_PRESS + 120, 36000 + 1, 120))

SINGLE_C_EVENTS = (
    f"VH_PAD frame={FIRST_PRESS} button=START action=PRESS\n"
    f"VH_PAD frame={FIRST_RELEASE} button=START action=RELEASE\n"
    f"VH_PAD frame={CONFIRM_PRESS} button=C action=PRESS\n"
    f"VH_PAD frame={CONFIRM_RELEASE} button=C action=RELEASE\n"
    f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n"
).encode("ascii")
SINGLE_C_STATE = (
    "VH_PADSTATE initial_start_bit=1\n"
    "VH_PADSTATE initial_confirm_button=C active_low_bit=1\n"
    f"VH_PADSTATE frame={FIRST_PRESS} start_bit=0\n"
    f"VH_PADSTATE frame={FIRST_RELEASE} start_bit=1\n"
    f"VH_PADSTATE frame={CONFIRM_PRESS} button=C active_low_bit=0\n"
    f"VH_PADSTATE frame={CONFIRM_RELEASE} button=C active_low_bit=1\n"
    f"VH_PADSTATE mode=1 completed_frames={FRAME_COUNT}\n"
).encode("ascii")
DOUBLE_C_EVENTS = (
    f"VH_PAD frame={FIRST_PRESS} button=START action=PRESS\n"
    f"VH_PAD frame={FIRST_RELEASE} button=START action=RELEASE\n"
    f"VH_PAD frame={CONFIRM_PRESS} button=C action=PRESS\n"
    f"VH_PAD frame={CONFIRM_RELEASE} button=C action=RELEASE\n"
    f"VH_PAD frame={CONFIRM2_PRESS} button=C action=PRESS\n"
    f"VH_PAD frame={CONFIRM2_RELEASE} button=C action=RELEASE\n"
    f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n"
).encode("ascii")
DOUBLE_C_STATE = (
    "VH_PADSTATE initial_start_bit=1\n"
    "VH_PADSTATE initial_confirm_button=C active_low_bit=1\n"
    f"VH_PADSTATE frame={FIRST_PRESS} start_bit=0\n"
    f"VH_PADSTATE frame={FIRST_RELEASE} start_bit=1\n"
    f"VH_PADSTATE frame={CONFIRM_PRESS} button=C active_low_bit=0\n"
    f"VH_PADSTATE frame={CONFIRM_RELEASE} button=C active_low_bit=1\n"
    f"VH_PADSTATE frame={CONFIRM2_PRESS} button=C active_low_bit=0\n"
    f"VH_PADSTATE frame={CONFIRM2_RELEASE} button=C active_low_bit=1\n"
    f"VH_PADSTATE mode=1 completed_frames={FRAME_COUNT}\n"
).encode("ascii")


def audit_private_prologue_continue(single_c: Path, double_c: Path) -> dict:
    if not single_c.is_absolute() or not double_c.is_absolute():
        raise ValueError("absolute private Stage116 output paths required")
    if single_c.resolve() == double_c.resolve():
        raise ValueError("two distinct Stage116 output directories required")
    _private_directory(single_c)
    _private_directory(double_c)
    if _private_regular(single_c / "pad-events.txt", 2048) != SINGLE_C_EVENTS:
        raise ValueError("Stage116 single-C controller receipt mismatch")
    if _private_regular(single_c / "pad-state.txt", 2048) != SINGLE_C_STATE:
        raise ValueError("Stage116 single-C active-low receipt mismatch")
    if _private_regular(double_c / "pad-events.txt", 2048) != DOUBLE_C_EVENTS:
        raise ValueError("Stage116 double-C controller receipt mismatch")
    if _private_regular(double_c / "pad-state.txt", 2048) != DOUBLE_C_STATE:
        raise ValueError("Stage116 second-C active-low receipt mismatch")

    single_count, single_dims = _check_long_frames(single_c)
    double_count, double_dims = _check_long_frames(double_c)
    if single_count != 400 or double_count != 400:
        raise ValueError("Stage116 checkpoint count mismatch")
    if single_dims != double_dims:
        raise ValueError("Stage116 final framebuffer geometries differ")

    for frame in PRE_FIRST_CHECKPOINTS:
        if not _equal_frame(single_c, double_c, frame):
            raise ValueError("Stage116 paired runs diverged before first START")
    for frame in PRE_FIRST_CONFIRM_CHECKPOINTS:
        if not _equal_frame(single_c, double_c, frame):
            raise ValueError("Stage116 paired runs diverged before first C confirm")

    pre_second_equal_count = sum(
        1 for frame in PRE_SECOND_CHECKPOINTS
        if _equal_frame(single_c, double_c, frame)
    )
    if pre_second_equal_count != len(PRE_SECOND_CHECKPOINTS):
        raise ValueError("Stage116 paired runs diverged before second C confirm")

    post_second_changes = [
        frame for frame in POST_SECOND_CHECKPOINTS
        if not _equal_frame(single_c, double_c, frame)
    ]
    post_second_changes_by_36k = [
        frame for frame in POST_SECOND_BY_36K_CHECKPOINTS
        if not _equal_frame(single_c, double_c, frame)
    ]
    if not post_second_changes_by_36k:
        raise ValueError("Stage116 second C had no framebuffer effect by frame 36000")

    single_cd, single_cd_hash = _count_canonical_fads(single_c)
    double_cd, double_cd_hash = _count_canonical_fads(double_c)
    return {
        "schema_version": 1,
        "kind": "STAGE116_PRIVATE_PROLOGUE_CONTINUE_INTEGRITY_ONLY",
        "frames_per_process": FRAME_COUNT,
        "paired_cold_boot_processes": 2,
        "checkpoint_png_count_per_process": 400,
        "all_checkpoint_pngs_and_diagnostic_sequences_verified": True,
        "same_dimensions_across_runs": True,
        "runs_identical_before_first_start": True,
        "runs_identical_through_frame_12120_before_first_C": True,
        "first_C_press_frame": CONFIRM_PRESS,
        "second_C_press_frame": CONFIRM2_PRESS,
        "second_C_release_frame": CONFIRM2_RELEASE,
        "all_pre_second_C_checkpoints_match": True,
        "pre_second_checkpoint_equal_count": pre_second_equal_count,
        "pre_second_checkpoint_total": len(PRE_SECOND_CHECKPOINTS),
        "first_post_second_C_framebuffer_divergence_by_36000": min(post_second_changes_by_36k),
        "first_post_second_C_framebuffer_divergence_through_48000": min(post_second_changes),
        "frame_32400_differs_after_second_C": not _equal_frame(single_c, double_c, 32400),
        "frame_48000_differs": not _equal_frame(single_c, double_c, 48000),
        "single_C_cd_event_count": single_cd,
        "double_C_cd_event_count": double_cd,
        "cd_logs_differ": single_cd_hash != double_cd_hash,
        "first_battle_or_player_control_verified": False,
        "requires_private_visual_review_of_dialogue_and_battle_state": True,
        "original_media_or_frame_hashes_exported": False,
    }


def _run_one(executable: Path, cue: Path, directory: Path, *, second_c: bool, seconds: int) -> None:
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
        "VH_SATURN_CONFIRM_AT_FRAME": str(CONFIRM_PRESS),
        "VH_SATURN_CONFIRM_BUTTON": "C",
    }
    if second_c:
        env["VH_SATURN_CONFIRM_AT_FRAME2"] = str(CONFIRM2_PRESS)
    process = subprocess.Popen(
        [str(executable), "vh-private-frame-boot", str(cue), str(FRAME_COUNT)],
        cwd=directory, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True, umask=0o077,
    )
    try:
        status = process.wait(timeout=seconds)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise ValueError("private Stage116 Saturn run timed out") from exc
    if status != 0:
        raise ValueError("private Stage116 Yabause process failed")
    if (directory / "gate").exists() or (directory / "gate").is_symlink():
        raise ValueError("private Stage116 CD capture gate was not closed")


def run_private_prologue_continue(
    cue: Path, track1: Path, track2: Path, executable: Path,
    expected_runner_sha256: str, single_c: Path, double_c: Path,
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
    outputs = (single_c, double_c)
    if any(not path.is_absolute() for path in outputs):
        raise ValueError("absolute private Stage116 output paths required")
    if single_c.resolve() == double_c.resolve():
        raise ValueError("two distinct Stage116 output directories required")
    for directory in outputs:
        _private_directory(directory)
        if any(directory.iterdir()):
            raise ValueError("Stage116 output directories must be fresh and empty")
    sources = {cue.resolve(), track1.resolve(), track2.resolve(), executable.resolve()}
    for directory in (single_c.resolve(), double_c.resolve()):
        if directory in sources or any(path in directory.parents for path in sources):
            raise ValueError("private output directory overlaps a source parent")
        if any(directory in path.parents for path in sources):
            raise ValueError("private output directory contains a source")
    initial_media = _check_media(manifest, pins)
    initial_runner = _fingerprint(executable)
    if initial_runner[1] != expected_runner_sha256:
        raise ValueError("public Yabause executable did not match independent SHA-256")

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = (
                pool.submit(_run_one, executable, cue, single_c, second_c=False, seconds=seconds),
                pool.submit(_run_one, executable, cue, double_c, second_c=True, seconds=seconds),
            )
            for future in futures:
                future.result()
    finally:
        try:
            if _check_media(manifest, pins) != initial_media:
                raise ValueError("original Saturn source changed during Stage116")
        except (OSError, ValueError) as exc:
            raise ValueError("original Saturn source changed during Stage116") from exc
        if _fingerprint(executable) != initial_runner:
            raise ValueError("public Yabause executable changed during Stage116")
    report = audit_private_prologue_continue(single_c, double_c)
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
    for flag in ("cue", "track1", "track2", "executable", "single-c", "double-c"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--timeout", type=int, default=7200)
    args = parser.parse_args()
    try:
        report = run_private_prologue_continue(
            args.cue, args.track1, args.track2, args.executable,
            args.expected_runner_sha256, args.single_c, args.double_c,
            seconds=args.timeout,
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        print("STAGE116_PRIVATE_PROLOGUE_CONTINUE_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
