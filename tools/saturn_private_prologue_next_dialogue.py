#!/usr/bin/env python3
"""Stage117 private paired 48,000-frame test for a third C dialogue press."""
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
from tools.saturn_private_first_battle_window import (
    CHECKPOINTS, FRAME_COUNT, _check_long_frames, _equal_frame,
)
from tools.saturn_private_original_start_pair import _build_manifest, _check_media
from tools.saturn_private_original_start_sequence import MAX_SECONDS, SHA256
from tools.saturn_private_prologue_continue import (
    CONFIRM2_PRESS, CONFIRM2_RELEASE, DOUBLE_C_EVENTS, DOUBLE_C_STATE,
    _validate_pair_path_shape,
)
from tools.saturn_private_start_ab import _count_canonical_fads

CONFIRM3_PRESS = 42000
CONFIRM3_RELEASE = 42006
PRE_THIRD_CHECKPOINTS = tuple(frame for frame in CHECKPOINTS if frame < CONFIRM3_PRESS)
POST_THIRD_CHECKPOINTS = tuple(frame for frame in CHECKPOINTS if frame > CONFIRM3_PRESS)
POST_THIRD_OBSERVATION_END = FRAME_COUNT

_TRIPLE_EVENT_TAIL = f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n".encode("ascii")
_TRIPLE_STATE_TAIL = f"VH_PADSTATE mode=1 completed_frames={FRAME_COUNT}\n".encode("ascii")
TRIPLE_C_EVENTS = DOUBLE_C_EVENTS.replace(
    _TRIPLE_EVENT_TAIL,
    (
        f"VH_PAD frame={CONFIRM3_PRESS} button=C action=PRESS\n"
        f"VH_PAD frame={CONFIRM3_RELEASE} button=C action=RELEASE\n"
    ).encode("ascii") + _TRIPLE_EVENT_TAIL,
)
TRIPLE_C_STATE = DOUBLE_C_STATE.replace(
    _TRIPLE_STATE_TAIL,
    (
        f"VH_PADSTATE frame={CONFIRM3_PRESS} button=C active_low_bit=0\n"
        f"VH_PADSTATE frame={CONFIRM3_RELEASE} button=C active_low_bit=1\n"
    ).encode("ascii") + _TRIPLE_STATE_TAIL,
)


def audit_private_prologue_next_dialogue(double_c: Path, triple_c: Path) -> dict:
    if not double_c.is_absolute() or not triple_c.is_absolute():
        raise ValueError("absolute private Stage117 output paths required")
    if double_c.resolve() == triple_c.resolve():
        raise ValueError("two distinct Stage117 output directories required")
    _validate_pair_path_shape(double_c, triple_c)
    _private_directory(double_c)
    _private_directory(triple_c)
    if _private_regular(double_c / "pad-events.txt", 2048) != DOUBLE_C_EVENTS:
        raise ValueError("Stage117 double-C controller receipt mismatch")
    if _private_regular(double_c / "pad-state.txt", 2048) != DOUBLE_C_STATE:
        raise ValueError("Stage117 double-C active-low receipt mismatch")
    if _private_regular(triple_c / "pad-events.txt", 2048) != TRIPLE_C_EVENTS:
        raise ValueError("Stage117 triple-C controller receipt mismatch")
    if _private_regular(triple_c / "pad-state.txt", 2048) != TRIPLE_C_STATE:
        raise ValueError("Stage117 third-C active-low receipt mismatch")

    double_count, double_dims = _check_long_frames(double_c)
    triple_count, triple_dims = _check_long_frames(triple_c)
    if double_count != 400 or triple_count != 400:
        raise ValueError("Stage117 checkpoint count mismatch")
    if double_dims != triple_dims:
        raise ValueError("Stage117 final framebuffer geometries differ")

    for frame in PRE_THIRD_CHECKPOINTS:
        if not _equal_frame(double_c, triple_c, frame):
            raise ValueError("Stage117 paired runs diverged before third C confirm")

    changed = [
        frame for frame in POST_THIRD_CHECKPOINTS
        if not _equal_frame(double_c, triple_c, frame)
    ]
    if not changed:
        raise ValueError("Stage117 third C had no framebuffer effect by frame 48000")

    double_cd, double_cd_hash = _count_canonical_fads(double_c)
    triple_cd, triple_cd_hash = _count_canonical_fads(triple_c)
    return {
        "schema_version": 1,
        "kind": "STAGE117_PRIVATE_PROLOGUE_NEXT_DIALOGUE_INTEGRITY_ONLY",
        "frames_per_process": FRAME_COUNT,
        "paired_cold_boot_processes": 2,
        "checkpoint_png_count_per_process": 400,
        "all_checkpoint_pngs_and_diagnostic_sequences_verified": True,
        "same_dimensions_across_runs": True,
        "second_C_press_frame": CONFIRM2_PRESS,
        "third_C_press_frame": CONFIRM3_PRESS,
        "third_C_release_frame": CONFIRM3_RELEASE,
        "pre_third_checkpoint_equal_count": len(PRE_THIRD_CHECKPOINTS),
        "pre_third_checkpoint_total": len(PRE_THIRD_CHECKPOINTS),
        "all_pre_third_C_checkpoints_match": True,
        "post_third_observation_end": POST_THIRD_OBSERVATION_END,
        "first_post_third_C_framebuffer_divergence": min(changed),
        "frame_48000_differs_after_third_C": not _equal_frame(double_c, triple_c, FRAME_COUNT),
        "double_C_cd_event_count": double_cd,
        "triple_C_cd_event_count": triple_cd,
        "cd_logs_differ": double_cd_hash != triple_cd_hash,
        "first_battle_or_player_control_verified": False,
        "requires_private_visual_review_of_dialogue_and_battle_state": True,
        "original_media_or_frame_hashes_exported": False,
    }


def _run_one(
    executable: Path, cue: Path, directory: Path, *, third_c: bool, seconds: int,
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
        "VH_SATURN_START_AT_FRAME": "12060",
        "VH_SATURN_CONFIRM_AT_FRAME": "12240",
        "VH_SATURN_CONFIRM_BUTTON": "C",
        "VH_SATURN_CONFIRM_AT_FRAME2": str(CONFIRM2_PRESS),
        "VH_SATURN_CONFIRM2_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME3": str(CONFIRM3_PRESS),
        "VH_SATURN_CONFIRM3_ENABLED": "1" if third_c else "0",
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
        raise ValueError("private Stage117 Saturn run timed out") from exc
    if status != 0:
        raise ValueError("private Stage117 Yabause process failed")
    if (directory / "gate").exists() or (directory / "gate").is_symlink():
        raise ValueError("private Stage117 CD capture gate was not closed")


def run_private_prologue_next_dialogue(
    cue: Path, track1: Path, track2: Path, executable: Path,
    expected_runner_sha256: str, double_c: Path, triple_c: Path,
    *, seconds: int = 7200, pins: dict = PINNED,
) -> dict:
    if not isinstance(expected_runner_sha256, str) or not SHA256.fullmatch(expected_runner_sha256):
        raise ValueError("independent lowercase SHA-256 of public Stage117 runner required")
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
    outputs = (double_c, triple_c)
    if any(not path.is_absolute() for path in outputs):
        raise ValueError("absolute private Stage117 output paths required")
    if double_c.resolve() == triple_c.resolve():
        raise ValueError("two distinct Stage117 output directories required")
    _validate_pair_path_shape(double_c, triple_c)
    for directory in outputs:
        _private_directory(directory)
        if any(directory.iterdir()):
            raise ValueError("Stage117 output directories must be fresh and empty")
    sources = {cue.resolve(), track1.resolve(), track2.resolve(), executable.resolve()}
    for directory in (double_c.resolve(), triple_c.resolve()):
        if directory in sources or any(path in directory.parents for path in sources):
            raise ValueError("private output directory overlaps a source parent")
        if any(directory in path.parents for path in sources):
            raise ValueError("private output directory contains a source")
    initial_media = _check_media(manifest, pins)
    initial_runner = _fingerprint(executable)
    if initial_runner[1] != expected_runner_sha256:
        raise ValueError("public Stage117 Yabause executable did not match independent SHA-256")

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = (
                pool.submit(_run_one, executable, cue, double_c, third_c=False, seconds=seconds),
                pool.submit(_run_one, executable, cue, triple_c, third_c=True, seconds=seconds),
            )
            for future in futures:
                future.result()
    finally:
        try:
            if _check_media(manifest, pins) != initial_media:
                raise ValueError("original Saturn source changed during Stage117")
        except (OSError, ValueError) as exc:
            raise ValueError("original Saturn source changed during Stage117") from exc
        if _fingerprint(executable) != initial_runner:
            raise ValueError("public Stage117 Yabause executable changed during run")

    report = audit_private_prologue_next_dialogue(double_c, triple_c)
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
    for flag in ("cue", "track1", "track2", "executable", "double-c", "triple-c"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--timeout", type=int, default=7200)
    args = parser.parse_args()
    try:
        report = run_private_prologue_next_dialogue(
            args.cue, args.track1, args.track2, args.executable,
            args.expected_runner_sha256, args.double_c, args.triple_c,
            seconds=args.timeout,
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        print("STAGE117_PRIVATE_PROLOGUE_NEXT_DIALOGUE_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
