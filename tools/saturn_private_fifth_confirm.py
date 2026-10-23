#!/usr/bin/env python3
"""Stage119: privately compare the fourth-C baseline against a fifth C at frame 45600."""
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
from tools.saturn_private_first_battle_window import CHECKPOINTS, FRAME_COUNT, _check_long_frames, _equal_frame
from tools.saturn_private_prologue_continue_fourth_c import (
    CONFIRM_PRESS, CONFIRM2_PRESS, CONFIRM3_PRESS, CONFIRM4_PRESS,
    QUAD_C_EVENTS, QUAD_C_STATE,
)

CONFIRM5_PRESS = 45600
CONFIRM5_RELEASE = 45606
PRE_FIFTH_CHECKPOINTS = tuple(f for f in CHECKPOINTS if f < CONFIRM5_PRESS)
POST_FIFTH_BY_46800 = tuple(f for f in CHECKPOINTS if CONFIRM5_PRESS < f <= 46800)
POST_FIFTH_CHECKPOINTS = tuple(f for f in CHECKPOINTS if f > CONFIRM5_PRESS)
TERMINAL_EVENT = f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n".encode("ascii")
TERMINAL_STATE = f"VH_PADSTATE mode=1 completed_frames={FRAME_COUNT}\n".encode("ascii")
FIVE_C_EVENTS = QUAD_C_EVENTS.replace(
    TERMINAL_EVENT,
    (f"VH_PAD frame={CONFIRM5_PRESS} button=C action=PRESS\n"
     f"VH_PAD frame={CONFIRM5_RELEASE} button=C action=RELEASE\n").encode("ascii") + TERMINAL_EVENT,
)
FIVE_C_STATE = QUAD_C_STATE.replace(
    TERMINAL_STATE,
    (f"VH_PADSTATE frame={CONFIRM5_PRESS} button=C active_low_bit=0\n"
     f"VH_PADSTATE frame={CONFIRM5_RELEASE} button=C active_low_bit=1\n").encode("ascii") + TERMINAL_STATE,
)


def _paired_paths(fourth_c: Path, fifth_c: Path) -> None:
    if (not fourth_c.is_absolute() or not fifth_c.is_absolute() or
            fourth_c.resolve() == fifth_c.resolve()):
        raise ValueError("distinct absolute Stage119 output paths required")
    a, b = fourth_c.resolve(), fifth_c.resolve()
    if a.parent != b.parent or len(str(a)) != len(str(b)):
        raise ValueError("equal-length sibling paths required for Stage119")


def audit_private_fifth_confirm(fourth_c: Path, fifth_c: Path) -> dict:
    _paired_paths(fourth_c, fifth_c)
    for folder in (fourth_c, fifth_c):
        _private_directory(folder)
    for folder, events, state in (
        (fourth_c, QUAD_C_EVENTS, QUAD_C_STATE),
        (fifth_c, FIVE_C_EVENTS, FIVE_C_STATE),
    ):
        if _private_regular(folder / "pad-events.txt", 2048) != events:
            raise ValueError("Stage119 pad event receipt mismatch")
        if _private_regular(folder / "pad-state.txt", 2048) != state:
            raise ValueError("Stage119 active-low pad-state receipt mismatch")
    a_pre = _private_regular(fourth_c / "pre.png", MAX_PNG_BYTES)
    b_pre = _private_regular(fifth_c / "pre.png", MAX_PNG_BYTES)
    if (a_pre != b_pre or validate_png_file(a_pre) != validate_png_file(b_pre)):
        raise ValueError("Stage119 boot frame differs before input")
    a_count, a_dims = _check_long_frames(fourth_c)
    b_count, b_dims = _check_long_frames(fifth_c)
    if a_count != 400 or b_count != 400 or a_dims != b_dims:
        raise ValueError("Stage119 checkpoint counts/geometry differ")
    for f in PRE_FIFTH_CHECKPOINTS:
        if not _equal_frame(fourth_c, fifth_c, f):
            raise ValueError("Stage119 divergence before fifth C")
    changed_early = [
        f for f in POST_FIFTH_BY_46800 if not _equal_frame(fourth_c, fifth_c, f)
    ]
    if not changed_early:
        raise ValueError("Stage119 fifth C had no framebuffer effect by 46800")
    a_cd, a_hash = _count_canonical_fads(fourth_c)
    b_cd, b_hash = _count_canonical_fads(fifth_c)
    return {
        "schema_version": 1,
        "kind": "STAGE119_PRIVATE_FIFTH_CONFIRM_INTEGRITY_ONLY",
        "frames_per_process": FRAME_COUNT,
        "checkpoint_png_count_per_process": 400,
        "diagnostic_samples_per_log": 402,
        "paired_cold_boot_processes": 2,
        "fifth_C_press_frame": CONFIRM5_PRESS,
        "fifth_C_release_frame": CONFIRM5_RELEASE,
        "all_pre_fifth_C_checkpoints_match": True,
        "pre_fifth_checkpoint_equal_count": len(PRE_FIFTH_CHECKPOINTS),
        "first_post_fifth_framebuffer_divergence_by_46800": min(changed_early),
        "frame_48000_differs": not _equal_frame(fourth_c, fifth_c, FRAME_COUNT),
        "fourth_C_cd_event_count": a_cd,
        "fifth_C_cd_event_count": b_cd,
        "cd_logs_differ": a_hash != b_hash,
        "first_controllable_tactical_battle_verified": False,
        "requires_private_visual_review": True,
        "original_media_or_frame_hashes_exported": False,
    }


def _run_one(executable: Path, cue: Path, folder: Path, *, fifth_c: bool, seconds: int) -> None:
    env = {
        "HOME": str(folder), "TMPDIR": str(folder), "PATH": os.defpath,
        "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
        "VH_SATURN_CAPTURE_GATE": str(folder / "gate"),
        "VH_SATURN_FAD_LOG": str(folder / "fad.vhcdlog"),
        "VH_SATURN_PRIVATE_FRAMES_DIR": str(folder),
        "VH_SATURN_START_AT_FRAME": str(FIRST_PRESS),
        "VH_SATURN_CONFIRM_AT_FRAME": str(CONFIRM_PRESS),
        "VH_SATURN_CONFIRM_BUTTON": "C",
        "VH_SATURN_CONFIRM_AT_FRAME2": str(CONFIRM2_PRESS),
        "VH_SATURN_CONFIRM2_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME3": str(CONFIRM3_PRESS),
        "VH_SATURN_CONFIRM3_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME4": str(CONFIRM4_PRESS),
        "VH_SATURN_CONFIRM4_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME5": str(CONFIRM5_PRESS),
        "VH_SATURN_CONFIRM5_ENABLED": "1" if fifth_c else "0",
    }
    p = subprocess.Popen(
        [str(executable), "vh-private-frame-boot", str(cue), str(FRAME_COUNT)],
        cwd=folder, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True, umask=0o077,
    )
    try:
        status = p.wait(timeout=seconds)
    except subprocess.TimeoutExpired as exc:
        try: os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        p.wait()
        raise ValueError("Stage119 private runner timed out") from exc
    if status != 0:
        raise ValueError("Stage119 private runner failed")
    if (folder / "gate").exists() or (folder / "gate").is_symlink():
        raise ValueError("Stage119 private CD capture gate did not close")


def run_private_fifth_confirm(
    cue: Path, track1: Path, track2: Path, executable: Path,
    runner_sha256: str, fourth_c: Path, fifth_c: Path,
    *, seconds: int = 7200, pins: dict = PINNED,
) -> dict:
    if not isinstance(runner_sha256, str) or not SHA256.fullmatch(runner_sha256):
        raise ValueError("independent runner SHA-256 required")
    if type(seconds) is not int or not 1 <= seconds <= MAX_SECONDS:
        raise ValueError("invalid bounded private timeout")
    if not executable.is_absolute() or executable.is_symlink():
        raise ValueError("absolute nonsymlinked public runner required")
    _not_in_checkout(executable)
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError("public runner must be executable")
    manifest = _build_manifest(cue, track1, track2)
    _paired_paths(fourth_c, fifth_c)
    for folder in (fourth_c, fifth_c):
        _private_directory(folder)
        if any(folder.iterdir()):
            raise ValueError("Stage119 output directories must be fresh and empty")
    sources = {cue.resolve(), track1.resolve(), track2.resolve(), executable.resolve()}
    for folder in (fourth_c.resolve(), fifth_c.resolve()):
        if folder in sources or any(src in folder.parents or folder in src.parents for src in sources):
            raise ValueError("Stage119 output directory overlaps a source")
    original = _check_media(manifest, pins)
    runner = _fingerprint(executable)
    if runner[1] != runner_sha256:
        raise ValueError("Stage119 executable digest mismatch")
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = (
                pool.submit(_run_one, executable, cue, fourth_c, fifth_c=False, seconds=seconds),
                pool.submit(_run_one, executable, cue, fifth_c, fifth_c=True, seconds=seconds),
            )
            for future in futures: future.result()
    finally:
        if _check_media(manifest, pins) != original:
            raise ValueError("Stage119 source media modified")
        if _fingerprint(executable) != runner:
            raise ValueError("Stage119 runner modified")
    report = audit_private_fifth_confirm(fourth_c, fifth_c)
    report.update({
        "same_original_media_before_after": True,
        "same_public_runner_identity_before_after": True,
        "both_processes_exited_successfully": True,
        "battle_control_claimed": False,
    })
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("cue", "track1", "track2", "executable", "fourth-c", "fifth-c"):
        parser.add_argument("--" + field, type=Path, required=True)
    parser.add_argument("--runner-sha256", required=True)
    parser.add_argument("--timeout", type=int, default=7200)
    args = parser.parse_args()
    try:
        report = run_private_fifth_confirm(
            args.cue, args.track1, args.track2, args.executable, args.runner_sha256,
            args.fourth_c, args.fifth_c, seconds=args.timeout,
        )
    except (ValueError, OSError, TypeError, subprocess.SubprocessError):
        print("STAGE119_PRIVATE_FIFTH_CONFIRM_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
