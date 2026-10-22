#!/usr/bin/env python3
"""Stage112 private A/B run: control versus two guarded Saturn START pulses.

This tool is for the user's local private workspace only. It never prints
original media paths, hashes, screenshots, or raw CD traces. Public CI must
only use synthetic inputs and must never invoke this tool against a real disc.
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

from tools.saturn_private_capture_cohort import _private_directory, _private_regular
from tools.saturn_private_capture_session import (
    PINNED, _fingerprint, _not_in_checkout, inspect_sources,
)
from tools.saturn_private_original_start_pair import _build_manifest, _check_media
from tools.saturn_private_start_ab import _count_canonical_fads, MAX_PNG_BYTES
from tools.saturn_private_frame_witness import validate_png_file

FRAME_COUNT = 24000
FIRST_PRESS = 12060
FIRST_RELEASE = 12066
SECOND_PRESS = 12240
SECOND_RELEASE = 12246
PRE_INPUT_FRAMES = (11880, 12000)
POST_INPUT_FRAMES = (12120, 12360, 13200, 18000, 24000)
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_SECONDS = 14400
FRAME_STATS = re.compile(
    rb"STAGE99_FRAMES (0|[1-9][0-9]*)\n"
    rb"STAGE99_PC_BEFORE (0|[1-9][0-9]*)\n"
    rb"STAGE99_PC_AFTER (0|[1-9][0-9]*)\n"
    rb"STAGE99_WIDTH (0|[1-9][0-9]*)\n"
    rb"STAGE99_HEIGHT (0|[1-9][0-9]*)\n\Z"
)
CONTROL_EVENTS = (
    f"VH_PAD mode=0 completed_frames={FRAME_COUNT}\n"
).encode("ascii")
START_EVENTS = (
    f"VH_PAD frame={FIRST_PRESS} button=START action=PRESS\n"
    f"VH_PAD frame={FIRST_RELEASE} button=START action=RELEASE\n"
    f"VH_PAD frame={SECOND_PRESS} button=START action=PRESS\n"
    f"VH_PAD frame={SECOND_RELEASE} button=START action=RELEASE\n"
    f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n"
).encode("ascii")
INITIAL = "VH_PADSTATE initial_start_bit=1\n"
CONTROL_STATE = (
    INITIAL + f"VH_PADSTATE mode=0 completed_frames={FRAME_COUNT}\n"
).encode("ascii")
START_STATE = (
    INITIAL +
    f"VH_PADSTATE frame={FIRST_PRESS} start_bit=0\n" +
    f"VH_PADSTATE frame={FIRST_RELEASE} start_bit=1\n" +
    f"VH_PADSTATE frame={SECOND_PRESS} start_bit=0\n" +
    f"VH_PADSTATE frame={SECOND_RELEASE} start_bit=1\n" +
    f"VH_PADSTATE mode=1 completed_frames={FRAME_COUNT}\n"
).encode("ascii")


def _fresh_dir(path: Path) -> None:
    _private_directory(path)
    if any(path.iterdir()):
        raise ValueError("private Stage112 run directories must be fresh and empty")


def _run_one(
    executable: Path, cue: Path, directory: Path, *, intervention: bool,
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
    if intervention:
        env["VH_SATURN_START_AT_FRAME"] = str(FIRST_PRESS)
        env["VH_SATURN_START_AT_FRAME2"] = str(SECOND_PRESS)
    process = subprocess.Popen(
        [str(executable), "vh-private-frame-boot", str(cue), str(FRAME_COUNT)],
        cwd=directory, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True, umask=0o077,
    )
    try:
        status = process.wait(timeout=seconds)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise ValueError("private Stage112 Saturn run timed out") from exc
    if status != 0:
        raise ValueError("private Stage112 Yabause process failed")
    if (directory / "gate").exists() or (directory / "gate").is_symlink():
        raise ValueError("private CD capture gate was not closed")


def _frame(directory: Path, frame: int) -> tuple[tuple[int, int], bytes]:
    raw = _private_regular(directory / f"frame-{frame}.png", MAX_PNG_BYTES)
    dims = validate_png_file(raw)
    if min(dims) < 64:
        raise ValueError("invalid private Saturn framebuffer dimensions")
    return dims, hashlib.sha256(raw).digest()


def _check_frames(directory: Path) -> tuple[int, tuple[int, int]]:
    expected = {f"frame-{n}.png" for n in range(120, FRAME_COUNT + 1, 120)}
    expected.update({"pre.png", "post.png", "frames.stats", "fad.vhcdlog",
                     "pad-events.txt", "pad-state.txt"})
    actual = {p.name for p in directory.iterdir()}
    if actual != expected:
        raise ValueError("private Stage112 output set incomplete or unexpected")
    for name in expected:
        entry = directory / name
        if entry.is_symlink() or not entry.is_file():
            raise ValueError("private Stage112 output contains a non-regular file")
    for n in range(120, FRAME_COUNT + 1, 120):
        dims = validate_png_file(_private_regular(directory / f"frame-{n}.png", MAX_PNG_BYTES))
        if not (64 <= dims[0] <= 704 and 64 <= dims[1] <= 512):
            raise ValueError("private Stage112 checkpoint dimensions invalid")
    raw = _private_regular(directory / "frames.stats", 256)
    match = FRAME_STATS.fullmatch(raw)
    if not match:
        raise ValueError("private Stage112 frame statistics malformed")
    completed, pc_before, pc_after, width, height = map(int, match.groups())
    if completed != FRAME_COUNT or pc_before > 0xFFFFFFFF or pc_after > 0xFFFFFFFF:
        raise ValueError("private Stage112 frame counter mismatch")
    if not (64 <= width <= 704 and 64 <= height <= 512):
        raise ValueError("private Stage112 final framebuffer dimensions invalid")
    final_dims, _ = _frame(directory, FRAME_COUNT)
    if final_dims != (width, height):
        raise ValueError("private Stage112 final PNG disagrees with frame statistics")
    for name in ("pre.png", "post.png"):
        dims = validate_png_file(_private_regular(directory / name, MAX_PNG_BYTES))
        if dims != final_dims:
            raise ValueError("private Stage112 pre/post framebuffer geometry mismatch")
    return FRAME_COUNT // 120, final_dims


def audit_private_start_sequence(control: Path, intervention: Path) -> dict:
    if (not control.is_absolute() or not intervention.is_absolute() or
            control.resolve() == intervention.resolve()):
        raise ValueError("two distinct absolute private workspaces required")
    _private_directory(control)
    _private_directory(intervention)
    if _private_regular(control / "pad-events.txt", 512) != CONTROL_EVENTS:
        raise ValueError("private Stage112 control pad receipt mismatch")
    if _private_regular(intervention / "pad-events.txt", 1024) != START_EVENTS:
        raise ValueError("private Stage112 dual START event receipt mismatch")
    if _private_regular(control / "pad-state.txt", 512) != CONTROL_STATE:
        raise ValueError("private Stage112 control active-low bit receipt mismatch")
    if _private_regular(intervention / "pad-state.txt", 1024) != START_STATE:
        raise ValueError("private Stage112 dual active-low bit receipt mismatch")

    control_count, control_dims = _check_frames(control)
    intervention_count, intervention_dims = _check_frames(intervention)
    if control_count != FRAME_COUNT // 120 or intervention_count != FRAME_COUNT // 120:
        raise ValueError("private Stage112 checkpoint count mismatch")
    if control_dims != intervention_dims:
        raise ValueError("private Stage112 final framebuffer geometries differ")

    agreement = {}
    for frame in PRE_INPUT_FRAMES + POST_INPUT_FRAMES:
        a_dims, a_hash = _frame(control, frame)
        b_dims, b_hash = _frame(intervention, frame)
        if a_dims != b_dims:
            raise ValueError("private Stage112 A/B framebuffer geometries differ")
        agreement[frame] = a_hash == b_hash
    if not all(agreement[n] for n in PRE_INPUT_FRAMES):
        raise ValueError("private Stage112 control and intervention diverged before first input")
    if agreement[12120] or agreement[13200]:
        raise ValueError("private Stage112 first title-to-menu response not present in A/B frames")

    control_fads, control_fad_hash = _count_canonical_fads(control)
    intervention_fads, intervention_fad_hash = _count_canonical_fads(intervention)
    return {
        "schema_version": 1,
        "kind": "STAGE112_PRIVATE_DUAL_START_AB_INTEGRITY_ONLY",
        "frames_per_process": FRAME_COUNT,
        "checkpoint_png_count_per_process": FRAME_COUNT // 120,
        "all_checkpoint_pngs_valid_and_sequential": True,
        "private_frame_stats_verified": True,
        "same_dimensions_and_pre_first_input_frames": True,
        "pre_first_input_frames_compared": list(PRE_INPUT_FRAMES),
        "post_input_frames_compared": list(POST_INPUT_FRAMES),
        "title_to_menu_response_visible_in_12120_and_13200_ab_comparison": True,
        "post_input_frame_equalities": {str(n): agreement[n] for n in POST_INPUT_FRAMES},
        "first_start_frame": FIRST_PRESS,
        "first_release_frame": FIRST_RELEASE,
        "second_start_frame": SECOND_PRESS,
        "second_release_frame": SECOND_RELEASE,
        "both_active_low_start_press_and_release_pairs_verified": True,
        "control_cd_event_count": control_fads,
        "intervention_cd_event_count": intervention_fads,
        "numeric_cd_logs_differ": control_fad_hash != intervention_fad_hash,
        "first_tactical_battle_verified": False,
        "requires_private_visual_review_for_battlefield": True,
        "original_media_or_frame_hashes_exported": False,
    }


def run_private_start_sequence(
    cue: Path, track1: Path, track2: Path, executable: Path,
    expected_runner_sha256: str, control: Path, intervention: Path,
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
    manifest = _build_manifest(cue, track1, track2)
    _fresh_dir(control)
    _fresh_dir(intervention)
    if control.resolve() == intervention.resolve():
        raise ValueError("control and intervention directories must be distinct")
    sources = {cue.resolve(), track1.resolve(), track2.resolve(), executable.resolve()}
    for directory in (control.resolve(), intervention.resolve()):
        if directory in sources or any(p in directory.parents for p in sources):
            raise ValueError("private output directory overlaps a source parent")
        if any(directory in p.parents for p in sources):
            raise ValueError("private output directory contains a source")
    initial_media = _check_media(manifest, pins)
    initial_runner = _fingerprint(executable)
    if initial_runner[1] != expected_runner_sha256:
        raise ValueError("public Yabause executable did not match independent SHA-256")

    for target, press in ((control, False), (intervention, True)):
        try:
            _run_one(executable, cue, target, intervention=press, seconds=seconds)
        finally:
            try:
                if _check_media(manifest, pins) != initial_media:
                    raise ValueError("original Saturn source changed during Stage112")
            except (OSError, ValueError) as exc:
                raise ValueError("original Saturn source changed during Stage112") from exc
            if _fingerprint(executable) != initial_runner:
                raise ValueError("public Yabause executable changed during Stage112")
    report = audit_private_start_sequence(control, intervention)
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
    for flag in ("cue", "track1", "track2", "executable", "control", "intervention"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--timeout", type=int, default=7200)
    args = parser.parse_args()
    try:
        report = run_private_start_sequence(
            args.cue, args.track1, args.track2, args.executable,
            args.expected_runner_sha256, args.control, args.intervention,
            seconds=args.timeout,
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        print("STAGE112_PRIVATE_DUAL_START_RUN_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
