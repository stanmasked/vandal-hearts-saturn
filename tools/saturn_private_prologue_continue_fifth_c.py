#!/usr/bin/env python3
"""Stage119 private paired 48,000-frame test for a fifth C dialogue press."""
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
from tools.saturn_private_original_start_sequence import FIRST_PRESS, MAX_SECONDS, SHA256
from tools.saturn_private_start_ab import MAX_PNG_BYTES, _count_canonical_fads
from tools.saturn_private_frame_witness import validate_png_file
from tools.saturn_private_first_battle_window import (
    CHECKPOINTS, FRAME_COUNT, _check_long_frames, _equal_frame,
)
from tools.saturn_private_prologue_continue_fourth_c import (
    QUAD_C_EVENTS, QUAD_C_STATE, TRIPLE_C_TERMINAL_EVENTS, TRIPLE_C_TERMINAL_STATE,
)

CONFIRM5_PRESS = 46000
CONFIRM5_RELEASE = 46006
PRE_FIRST_CHECKPOINTS = tuple(range(120, FIRST_PRESS, 120))
PRE_FIRST_CONFIRM_CHECKPOINTS = tuple(range(120, 12120 + 1, 120))
PRE_FIFTH_CHECKPOINTS = tuple(range(120, CONFIRM5_PRESS, 120))
POST_FIFTH_CHECKPOINTS = tuple(frame for frame in CHECKPOINTS if frame > CONFIRM5_PRESS)
POST_FIFTH_BY_47200_CHECKPOINTS = tuple(range(CONFIRM5_PRESS + 120, 47200 + 1, 120))
FIFTH_C_EVENTS = QUAD_C_EVENTS.replace(
    TRIPLE_C_TERMINAL_EVENTS,
    (
        f"VH_PAD frame={CONFIRM5_PRESS} button=C action=PRESS\n"
        f"VH_PAD frame={CONFIRM5_RELEASE} button=C action=RELEASE\n"
    ).encode("ascii") + TRIPLE_C_TERMINAL_EVENTS,
)
FIFTH_C_STATE = QUAD_C_STATE.replace(
    TRIPLE_C_TERMINAL_STATE,
    (
        f"VH_PADSTATE frame={CONFIRM5_PRESS} button=C active_low_bit=0\n"
        f"VH_PADSTATE frame={CONFIRM5_RELEASE} button=C active_low_bit=1\n"
    ).encode("ascii") + TRIPLE_C_TERMINAL_STATE,
)


def _validate_pair_path_shape(fourth_c: Path, fifth_c: Path) -> None:
    fourth_resolved = fourth_c.resolve()
    fifth_resolved = fifth_c.resolve()
    if fourth_resolved.parent != fifth_resolved.parent:
        raise ValueError("Stage119 paired output directories must share one parent")
    if len(str(fourth_resolved)) != len(str(fifth_resolved)):
        raise ValueError("Stage119 paired output paths must have equal length for matched environment shape")


def audit_private_prologue_continue_fifth_c(fourth_c: Path, fifth_c: Path) -> dict:
    if not fourth_c.is_absolute() or not fifth_c.is_absolute():
        raise ValueError("absolute private Stage119 output paths required")
    if fourth_c.resolve() == fifth_c.resolve():
        raise ValueError("two distinct Stage119 output directories required")
    _validate_pair_path_shape(fourth_c, fifth_c)
    _private_directory(fourth_c)
    _private_directory(fifth_c)
    if _private_regular(fourth_c / "pad-events.txt", 2048) != QUAD_C_EVENTS:
        raise ValueError("Stage119 fourth-C controller receipt mismatch")
    if _private_regular(fourth_c / "pad-state.txt", 2048) != QUAD_C_STATE:
        raise ValueError("Stage119 fourth-C active-low receipt mismatch")
    if _private_regular(fifth_c / "pad-events.txt", 2048) != FIFTH_C_EVENTS:
        raise ValueError("Stage119 fifth-C controller receipt mismatch")
    if _private_regular(fifth_c / "pad-state.txt", 2048) != FIFTH_C_STATE:
        raise ValueError("Stage119 fifth-C active-low receipt mismatch")

    fourth_pre = _private_regular(fourth_c / "pre.png", MAX_PNG_BYTES)
    fifth_pre = _private_regular(fifth_c / "pre.png", MAX_PNG_BYTES)
    if validate_png_file(fourth_pre) != validate_png_file(fifth_pre) or fourth_pre != fifth_pre:
        raise ValueError("Stage119 paired runs diverged before first START")

    fourth_count, fourth_dims = _check_long_frames(fourth_c)
    fifth_count, fifth_dims = _check_long_frames(fifth_c)
    if fourth_count != 400 or fifth_count != 400:
        raise ValueError("Stage119 checkpoint count mismatch")
    if fourth_dims != fifth_dims:
        raise ValueError("Stage119 final framebuffer geometries differ")

    for frame in PRE_FIRST_CHECKPOINTS:
        if not _equal_frame(fourth_c, fifth_c, frame):
            raise ValueError("Stage119 paired runs diverged before first START")
    for frame in PRE_FIRST_CONFIRM_CHECKPOINTS:
        if not _equal_frame(fourth_c, fifth_c, frame):
            raise ValueError("Stage119 paired runs diverged before first C confirm")

    pre_fifth_equal_count = sum(
        1 for frame in PRE_FIFTH_CHECKPOINTS
        if _equal_frame(fourth_c, fifth_c, frame)
    )
    if pre_fifth_equal_count != len(PRE_FIFTH_CHECKPOINTS):
        raise ValueError("Stage119 paired runs diverged before fifth C confirm")

    post_fifth_changes = [
        frame for frame in POST_FIFTH_CHECKPOINTS
        if not _equal_frame(fourth_c, fifth_c, frame)
    ]
    post_fifth_changes_by_47200 = [
        frame for frame in POST_FIFTH_BY_47200_CHECKPOINTS
        if not _equal_frame(fourth_c, fifth_c, frame)
    ]
    if not post_fifth_changes_by_47200:
        raise ValueError("Stage119 fifth C had no framebuffer effect by frame 47200")

    fourth_cd, fourth_cd_hash = _count_canonical_fads(fourth_c)
    fifth_cd, fifth_cd_hash = _count_canonical_fads(fifth_c)
    return {
        "schema_version": 1,
        "kind": "STAGE119_PRIVATE_PROLOGUE_CONTINUE_INTEGRITY_ONLY",
        "frames_per_process": FRAME_COUNT,
        "paired_cold_boot_processes": 2,
        "checkpoint_png_count_per_process": 400,
        "all_checkpoint_pngs_and_diagnostic_sequences_verified": True,
        "same_dimensions_across_runs": True,
        "fifth_C_press_frame": CONFIRM5_PRESS,
        "fifth_C_release_frame": CONFIRM5_RELEASE,
        "all_pre_fifth_C_checkpoints_match": True,
        "pre_fifth_checkpoint_equal_count": pre_fifth_equal_count,
        "pre_fifth_checkpoint_total": len(PRE_FIFTH_CHECKPOINTS),
        "first_post_fifth_C_framebuffer_divergence_by_47200": min(post_fifth_changes_by_47200),
        "first_post_fifth_C_framebuffer_divergence_through_48000": min(post_fifth_changes),
        "frame_48000_differs": not _equal_frame(fourth_c, fifth_c, FRAME_COUNT),
        "fourth_C_cd_event_count": fourth_cd,
        "fifth_C_cd_event_count": fifth_cd,
        "cd_logs_identical": fourth_cd_hash == fifth_cd_hash,
        "first_battle_or_player_control_verified": False,
        "requires_private_visual_review_of_dialogue_and_battle_state": True,
        "original_media_or_frame_hashes_exported": False,
    }


def _run_one(executable: Path, cue: Path, directory: Path, *, fifth_c: bool, seconds: int) -> None:
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
        "VH_SATURN_CONFIRM_AT_FRAME": "12240",
        "VH_SATURN_CONFIRM_BUTTON": "C",
        "VH_SATURN_CONFIRM_AT_FRAME2": "31200",
        "VH_SATURN_CONFIRM2_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME3": "36000",
        "VH_SATURN_CONFIRM3_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME4": "42000",
        "VH_SATURN_CONFIRM4_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME5": str(CONFIRM5_PRESS),
        "VH_SATURN_CONFIRM5_ENABLED": "1" if fifth_c else "0",
    }
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
        raise ValueError("private Stage119 Saturn run timed out") from exc
    if status != 0:
        raise ValueError("private Stage119 Yabause process failed")
    if (directory / "gate").exists() or (directory / "gate").is_symlink():
        raise ValueError("private Stage119 CD capture gate was not closed")


def run_private_prologue_continue_fifth_c(
    cue: Path, track1: Path, track2: Path, executable: Path,
    expected_runner_sha256: str, fourth_c: Path, fifth_c: Path,
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
    outputs = (fourth_c, fifth_c)
    if any(not path.is_absolute() for path in outputs):
        raise ValueError("absolute private Stage119 output paths required")
    if fourth_c.resolve() == fifth_c.resolve():
        raise ValueError("two distinct Stage119 output directories required")
    _validate_pair_path_shape(fourth_c, fifth_c)
    for directory in outputs:
        _private_directory(directory)
        if any(directory.iterdir()):
            raise ValueError("Stage119 output directories must be fresh and empty")
    sources = {cue.resolve(), track1.resolve(), track2.resolve(), executable.resolve()}
    for directory in (fourth_c.resolve(), fifth_c.resolve()):
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
                pool.submit(_run_one, executable, cue, fourth_c, fifth_c=False, seconds=seconds),
                pool.submit(_run_one, executable, cue, fifth_c, fifth_c=True, seconds=seconds),
            )
            for future in futures:
                future.result()
    finally:
        try:
            if _check_media(manifest, pins) != initial_media:
                raise ValueError("original Saturn source changed during Stage119")
        except (OSError, ValueError) as exc:
            raise ValueError("original Saturn source changed during Stage119") from exc
        if _fingerprint(executable) != initial_runner:
            raise ValueError("public Yabause runner changed during Stage119")

    report = audit_private_prologue_continue_fifth_c(fourth_c, fifth_c)
    report.update({
        "same_pinned_original_media_before_and_after_both_processes": True,
        "same_public_runner_file_identity_and_digest_before_and_after": True,
        "both_private_processes_returned_zero_status": True,
        "private_environment_allowlisted": True,
        "first_battle_claimed": False,
    })
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("cue", "track1", "track2", "executable", "fourth-c", "fifth-c"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--timeout", type=int, default=7200)
    args = parser.parse_args()
    try:
        report = run_private_prologue_continue_fifth_c(
            args.cue, args.track1, args.track2, args.executable,
            args.expected_runner_sha256, args.fourth_c, args.fifth_c,
            seconds=args.timeout,
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        print("STAGE119_PRIVATE_PROLOGUE_CONTINUE_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
