#!/usr/bin/env python3
"""Stage110: fail-closed PRIVATE execution of control and START Saturn sessions.

Never runs in public Actions against original media. Inputs must be full
Stage02-pinned translation-patched Track1/Track2/CUE and a separately
SHA-256-pinned *executable* from the Stage109 GCC/Clang public build. Both
runs use the same unmodified source and runner; all output stays in two
existing fresh private 0700 directories. No game bytes, frame hashes,
FAD addresses, paths or subprocess output are sent to stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys

from tools.saturn_private_capture_session import (
    PINNED, _fingerprint, _not_in_checkout, inspect_sources,
)
from tools.saturn_private_capture_cohort import _private_directory, _private_regular
from tools.saturn_private_frame_witness import validate_png_file
from tools.saturn_private_start_bit_ab import audit_native_padbit_ab
from tools.saturn_private_start_ab import MAX_PNG_BYTES

FRAME_COUNT = 13200
START_FRAME = 12060
PRE_INPUT_FRAMES = (11880, 12000)
POST_INPUT_FRAMES = (12120, 13200)
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_SECONDS = 14400


def _fresh_dir(path: Path) -> None:
    _private_directory(path)
    if any(path.iterdir()):
        raise ValueError("existing private run directory must be empty")


def _build_manifest(cue: Path, track1: Path, track2: Path) -> dict:
    if any(not p.is_absolute() or p.is_symlink() for p in (cue, track1, track2)):
        raise ValueError("original source paths must be absolute and nonsymlinked")
    if len({p.resolve() for p in (cue, track1, track2)}) != 3:
        raise ValueError("original source files cannot be aliases")
    # The exact pinned original CUE contains relative FILE directives.
    if track1.parent.resolve() != cue.parent.resolve() or track2.parent.resolve() != cue.parent.resolve():
        raise ValueError("CUE/Track1/Track2 must reside in the same private folder")
    return {
        "schema_version": 1,
        "product_code": "T-9526G",
        "release_kind": "translation_patched",
        "files": {"cue": str(cue), "track1": str(track1), "track2": str(track2)},
    }


def _check_media(manifest: dict, pins: dict) -> dict:
    return inspect_sources(manifest, pins=pins)


def _run_one(
    executable: Path, cue: Path, directory: Path, *, press_start: bool,
    seconds: int,
) -> None:
    # Never inherit an unintended previous private capture environment.
    env = {k: v for k, v in os.environ.items() if not k.startswith("VH_SATURN_")}
    env.update({
        "HOME": str(directory),
        "VH_SATURN_CAPTURE_GATE": str(directory / "gate"),
        "VH_SATURN_FAD_LOG": str(directory / "fad.vhcdlog"),
        "VH_SATURN_PRIVATE_FRAMES_DIR": str(directory),
    })
    if press_start:
        env["VH_SATURN_START_AT_FRAME"] = str(START_FRAME)
    cmd = [str(executable), "vh-private-frame-boot", str(cue), str(FRAME_COUNT)]
    process = subprocess.Popen(
        cmd, cwd=directory, env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True, umask=0o077,
    )
    try:
        result = process.wait(timeout=seconds)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise ValueError("private Saturn original-disc run timed out") from exc
    if result != 0:
        raise ValueError("private Yabause runner returned an error")
    if (directory / "gate").exists() or (directory / "gate").is_symlink():
        raise ValueError("private CD capture gate was not closed")


def _frame(directory: Path, n: int) -> tuple[tuple[int, int], bytes]:
    raw = _private_regular(directory / f"frame-{n}.png", MAX_PNG_BYTES)
    dimensions = validate_png_file(raw)
    if min(dimensions) < 64:
        raise ValueError("invalid original guest framebuffer dimensions")
    return dimensions, hashlib.sha256(raw).digest()


FRAME_STATS = re.compile(
    rb"STAGE99_FRAMES (0|[1-9][0-9]*)\n"
    rb"STAGE99_PC_BEFORE (0|[1-9][0-9]*)\n"
    rb"STAGE99_PC_AFTER (0|[1-9][0-9]*)\n"
    rb"STAGE99_WIDTH (0|[1-9][0-9]*)\n"
    rb"STAGE99_HEIGHT (0|[1-9][0-9]*)\n"
    rb"\Z"
)


def _verified_frame_stats(directory: Path) -> tuple[int, int]:
    """Bind Yabause's final frame accounting to the protected final PNG."""
    raw = _private_regular(directory / "frames.stats", 256)
    match = FRAME_STATS.fullmatch(raw)
    if not match:
        raise ValueError("private Yabause final frame accounting is malformed")
    completed, pc_before, pc_after, width, height = map(int, match.groups())
    if (completed != FRAME_COUNT or
            pc_before > 0xFFFFFFFF or pc_after > 0xFFFFFFFF or
            not (64 <= width <= 704 and 64 <= height <= 512)):
        raise ValueError("private Yabause did not finish the required frame contract")
    dimensions, _ = _frame(directory, FRAME_COUNT)
    if dimensions != (width, height):
        raise ValueError("Yabause final PNG dimensions differ from frame accounting")
    return dimensions


def audit_joint_evidence(control: Path, pressed: Path) -> dict:
    """Stage108-like pre-input PNG baseline plus Stage109 native padbit proof."""
    report = audit_native_padbit_ab(control, pressed)
    control_geometry = _verified_frame_stats(control)
    pressed_geometry = _verified_frame_stats(pressed)
    if control_geometry != pressed_geometry:
        raise ValueError("A/B Yabause final frame accounting dimensions differ")
    agreement = {}
    for n in PRE_INPUT_FRAMES + POST_INPUT_FRAMES:
        a_shape, a_hash = _frame(control, n)
        b_shape, b_hash = _frame(pressed, n)
        if a_shape != b_shape:
            raise ValueError("control/START framebuffer dimensions differ")
        agreement[n] = a_hash == b_hash
    if not all(agreement[n] for n in PRE_INPUT_FRAMES):
        raise ValueError("original A/B frame files diverged before START")
    return {
        **report,
        "schema_version": 3,
        "kind": "STAGE110_PRIVATE_ORIGINAL_START_AB_INTEGRITY_ONLY",
        "emulator_frame_stats_verified_in_both_processes": True,
        "completed_frames_from_both_emulator_stats": FRAME_COUNT,
        "final_frame_dimensions_crosschecked_to_both_stats": True,
        "pre_start_png_checkpoints_match": True,
        "pre_start_frames_compared": list(PRE_INPUT_FRAMES),
        "post_start_frames_compared": list(POST_INPUT_FRAMES),
        "post_start_12120_png_files_differ": not agreement[12120],
        "post_start_13200_png_files_differ": not agreement[13200],
        "actual_game_menu_visually_verified": False,
        "original_first_battle_verified": False,
    }


def run_original_pair(
    cue: Path, track1: Path, track2: Path,
    executable: Path, expected_runner_sha256: str,
    control: Path, pressed: Path, *, seconds: int = 1800,
    pins: dict = PINNED,
) -> dict:
    if not isinstance(expected_runner_sha256, str) or not SHA256.fullmatch(expected_runner_sha256):
        raise ValueError("independent lowercase SHA256 of public Yabause executable required")
    if type(seconds) is not int or not (1 <= seconds <= MAX_SECONDS):
        raise ValueError("invalid bounded private process timeout")
    if not executable.is_absolute() or executable.is_symlink():
        raise ValueError("absolute nonsymlinked public emulator executable required")
    _not_in_checkout(executable)
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError("public Yabause executable must be runnable")
    manifest = _build_manifest(cue, track1, track2)
    _fresh_dir(control)
    _fresh_dir(pressed)
    dirs = [(control.stat().st_dev, control.stat().st_ino),
            (pressed.stat().st_dev, pressed.stat().st_ino)]
    if (dirs[0] == dirs[1] or
            control.resolve() == pressed.resolve() or
            executable.resolve() in {cue.resolve(), track1.resolve(), track2.resolve()} or
            any(p.resolve() == d.resolve() for d in (control, pressed)
                for p in (cue.parent, executable.parent))):
        raise ValueError("workspace or source paths overlap")
    start_media = _check_media(manifest, pins)
    start_runner = _fingerprint(executable)
    if start_runner[1] != expected_runner_sha256:
        raise ValueError("public Yabause executable did not match independent SHA256")

    for target, press in ((control, False), (pressed, True)):
        try:
            _run_one(executable, cue, target, press_start=press, seconds=seconds)
        finally:
            # Always check both the *bytes* and file identity, even after
            # timeouts, errors or a malicious media-modifying subprocess.
            try:
                current_media = _check_media(manifest, pins)
            except (OSError, ValueError) as exc:
                raise ValueError("original Saturn source changed during execution") from exc
            if current_media != start_media:
                raise ValueError("original Saturn source changed during execution")
            if _fingerprint(executable) != start_runner:
                raise ValueError("Yabause executable changed during execution")

    result = audit_joint_evidence(control, pressed)
    result.update({
        "same_stage02_full_media_digest_before_and_after_both_processes": True,
        "same_public_runner_digest_and_file_identity_before_and_after": True,
        "two_processes_returned_zero_status": True,
        "source_game_media_or_frame_hashes_exported": False,
        "title_to_menu_verified_by_visual_inspection": False,
    })
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ("cue", "track1", "track2", "executable", "control", "start"):
        p.add_argument("--" + flag, type=Path, required=True)
    p.add_argument("--expected-runner-sha256", required=True)
    p.add_argument("--timeout", type=int, default=1800)
    a = p.parse_args()
    try:
        report = run_original_pair(
            a.cue, a.track1, a.track2, a.executable,
            a.expected_runner_sha256, a.control, a.start,
            seconds=a.timeout,
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        print("STAGE110_PRIVATE_ORIGINAL_AB_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
