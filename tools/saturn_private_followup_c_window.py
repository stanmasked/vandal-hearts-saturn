#!/usr/bin/env python3
"""Stage116 private paired 48,000-frame run to verify follow-up C dialogue input."""
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
    CHECKPOINTS, CONFIRM_EVENTS, CONFIRM_PRESS, CONFIRM_RELEASE, CONFIRM_STATE,
    FRAME_COUNT, _check_long_frames, _equal_frame,
)
from tools.saturn_private_original_start_pair import _build_manifest, _check_media
from tools.saturn_private_original_start_sequence import MAX_SECONDS, SHA256
from tools.saturn_private_start_ab import _count_canonical_fads, MAX_PNG_BYTES

FOLLOWUP_OBSERVATION_FRAMES = 6000


def _followup_receipts(frame: int) -> tuple[bytes, bytes]:
    if type(frame) is not int or not (
        CONFIRM_PRESS + 12 <= frame <= FRAME_COUNT - 8
    ):
        raise ValueError("invalid bounded Stage116 follow-up C frame")
    event_tail = f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n".encode("ascii")
    state_tail = f"VH_PADSTATE mode=1 completed_frames={FRAME_COUNT}\n".encode("ascii")
    events = CONFIRM_EVENTS.replace(
        event_tail,
        (
            f"VH_PAD frame={frame} button=C action=PRESS\n"
            f"VH_PAD frame={frame + 6} button=C action=RELEASE\n"
        ).encode("ascii") + event_tail,
    )
    state = CONFIRM_STATE.replace(
        state_tail,
        (
            f"VH_PADSTATE frame={frame} button=C active_low_bit=0\n"
            f"VH_PADSTATE frame={frame + 6} button=C active_low_bit=1\n"
        ).encode("ascii") + state_tail,
    )
    return events, state


def audit_private_followup_c_window(
    initial_c_only: Path, followup_c: Path, followup_c_frame: int
) -> dict:
    if not initial_c_only.is_absolute() or not followup_c.is_absolute():
        raise ValueError("absolute private Stage116 output paths required")
    if initial_c_only.resolve() == followup_c.resolve():
        raise ValueError("two distinct Stage116 output directories required")
    expected_events, expected_state = _followup_receipts(followup_c_frame)
    _private_directory(initial_c_only)
    _private_directory(followup_c)

    if _private_regular(initial_c_only / "pad-events.txt", 2048) != CONFIRM_EVENTS:
        raise ValueError("Stage116 initial-C control receipt mismatch")
    if _private_regular(initial_c_only / "pad-state.txt", 2048) != CONFIRM_STATE:
        raise ValueError("Stage116 initial-C control active-low receipt mismatch")
    if _private_regular(followup_c / "pad-events.txt", 2048) != expected_events:
        raise ValueError("Stage116 follow-up-C controller receipt mismatch")
    if _private_regular(followup_c / "pad-state.txt", 2048) != expected_state:
        raise ValueError("Stage116 follow-up-C active-low receipt mismatch")

    control_count, control_dims = _check_long_frames(initial_c_only)
    followup_count, followup_dims = _check_long_frames(followup_c)
    if control_count != 400 or followup_count != 400:
        raise ValueError("Stage116 checkpoint count mismatch")
    if control_dims != followup_dims:
        raise ValueError("Stage116 framebuffer geometries differ")

    pre_followup_checkpoints = tuple(
        frame for frame in CHECKPOINTS if frame < followup_c_frame
    )
    for frame in pre_followup_checkpoints:
        if not _equal_frame(initial_c_only, followup_c, frame):
            raise ValueError("Stage116 runs diverged before the follow-up C pulse")

    observation_end = min(FRAME_COUNT, followup_c_frame + FOLLOWUP_OBSERVATION_FRAMES)
    observation_checkpoints = tuple(
        frame for frame in CHECKPOINTS
        if followup_c_frame < frame <= observation_end
    )
    if not observation_checkpoints:
        raise ValueError("Stage116 follow-up observation window is empty")
    changed = [
        frame for frame in observation_checkpoints
        if not _equal_frame(initial_c_only, followup_c, frame)
    ]
    if not changed:
        raise ValueError("Stage116 follow-up C produced no framebuffer divergence in the observation window")

    checkpoints_of_interest = (
        followup_c_frame + 120,
        min(FRAME_COUNT, followup_c_frame + 6000),
        48000,
    )
    checkpoint_equalities = {
        str(frame): _equal_frame(initial_c_only, followup_c, frame)
        for frame in checkpoints_of_interest if frame in CHECKPOINTS
    }
    control_cd, control_cd_digest = _count_canonical_fads(initial_c_only)
    followup_cd, followup_cd_digest = _count_canonical_fads(followup_c)
    return {
        "schema_version": 1,
        "kind": "STAGE116_PRIVATE_FOLLOWUP_C_INTEGRITY_ONLY",
        "frames_per_process": FRAME_COUNT,
        "independent_cold_boot_processes": 2,
        "checkpoint_png_count_per_process": 400,
        "all_checkpoint_pngs_valid_and_sequential": True,
        "private_frame_stats_and_diagnostic_sequences_verified": True,
        "same_dimensions_across_runs": True,
        "initial_c_confirm_receipts_verified": True,
        "followup_c_frame": followup_c_frame,
        "followup_c_release_frame": followup_c_frame + 6,
        "checkpoints_compared_before_followup": len(pre_followup_checkpoints),
        "runs_identical_through_frame": max(pre_followup_checkpoints),
        "followup_observation_window_end": observation_end,
        "followup_observation_checkpoints_compared": len(observation_checkpoints),
        "first_followup_c_divergence_frame": min(changed),
        "post_followup_checkpoint_equalities": checkpoint_equalities,
        "cd_event_count_initial_c_only": control_cd,
        "cd_event_count_followup_c": followup_cd,
        "cd_logs_differ": control_cd_digest != followup_cd_digest,
        "followup_input_effect_verified_numerically": True,
        "first_battle_or_player_control_verified": False,
        "requires_private_visual_review_of_late_frames": True,
        "original_media_or_frame_hashes_exported": False,
    }


def _fresh_dir(path: Path) -> None:
    _private_directory(path)
    if any(path.iterdir()):
        raise ValueError("Stage116 output directories must be fresh and empty")


def _run_one(
    executable: Path, cue: Path, directory: Path, *,
    followup_c_frame: int | None, seconds: int,
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
        "VH_SATURN_CONFIRM_AT_FRAME": str(CONFIRM_PRESS),
        "VH_SATURN_CONFIRM_BUTTON": "C",
    }
    if followup_c_frame is not None:
        env["VH_SATURN_FOLLOWUP_C_AT_FRAME"] = str(followup_c_frame)
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
        raise ValueError("private Stage116 Saturn run timed out") from exc
    if status != 0:
        raise ValueError("private Stage116 Yabause process failed")
    if (directory / "gate").exists() or (directory / "gate").is_symlink():
        raise ValueError("private Stage116 CD capture gate was not closed")


def run_private_followup_c_window(
    cue: Path, track1: Path, track2: Path, executable: Path,
    expected_runner_sha256: str, initial_c_only: Path, followup_c: Path,
    *, followup_c_frame: int = 30000, seconds: int = 7200, pins: dict = PINNED,
) -> dict:
    _followup_receipts(followup_c_frame)
    if not isinstance(expected_runner_sha256, str) or not SHA256.fullmatch(expected_runner_sha256):
        raise ValueError("independent lowercase SHA-256 of public Stage116 runner required")
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
    outputs = (initial_c_only, followup_c)
    if any(not path.is_absolute() for path in outputs):
        raise ValueError("absolute private Stage116 output paths required")
    if initial_c_only.resolve() == followup_c.resolve():
        raise ValueError("two distinct Stage116 output directories required")
    for directory in outputs:
        _fresh_dir(directory)
    sources = {cue.resolve(), track1.resolve(), track2.resolve(), executable.resolve()}
    for directory in (initial_c_only.resolve(), followup_c.resolve()):
        if directory in sources or any(path in directory.parents for path in sources):
            raise ValueError("private output directory overlaps a source parent")
        if any(directory in path.parents for path in sources):
            raise ValueError("private output directory contains a source")
    initial_media = _check_media(manifest, pins)
    initial_runner = _fingerprint(executable)
    if initial_runner[1] != expected_runner_sha256:
        raise ValueError("public Stage116 Yabause executable did not match independent SHA-256")

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = (
                pool.submit(
                    _run_one, executable, cue, initial_c_only,
                    followup_c_frame=None, seconds=seconds,
                ),
                pool.submit(
                    _run_one, executable, cue, followup_c,
                    followup_c_frame=followup_c_frame, seconds=seconds,
                ),
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
            raise ValueError("public Stage116 Yabause executable changed during run")

    report = audit_private_followup_c_window(
        initial_c_only, followup_c, followup_c_frame
    )
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
    for flag in ("cue", "track1", "track2", "executable", "initial-c-only", "followup-c"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--followup-c-frame", type=int, default=30000)
    parser.add_argument("--timeout", type=int, default=7200)
    args = parser.parse_args()
    try:
        report = run_private_followup_c_window(
            args.cue, args.track1, args.track2, args.executable,
            args.expected_runner_sha256, args.initial_c_only, args.followup_c,
            followup_c_frame=args.followup_c_frame, seconds=args.timeout,
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        print("STAGE116_PRIVATE_FOLLOWUP_C_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
