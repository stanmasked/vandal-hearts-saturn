#!/usr/bin/env python3
"""Stage145 private paired runner; requires verified owner-only Stage144 Drive readback."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from tools.saturn_private_capture_cohort import _private_directory
from tools.saturn_private_capture_session import PINNED, _fingerprint, _not_in_checkout
from tools.saturn_private_original_start_pair import _build_manifest, _check_media
from tools.saturn_private_original_start_sequence import MAX_SECONDS, SHA256
from tools.saturn_private_stage144_archive_gate import verify_private_stage144_archive
from tools.saturn_private_prologue_continue_twelfth_c_audit import audit_private_prologue_continue_twelfth_c

FRAME_COUNT = 144000
CONFIRM10_PRESS = 108000
CONFIRM10_RELEASE = 108006
CONFIRM11_PRESS = 120000
CONFIRM11_RELEASE = 120006
CONFIRM12_PRESS = 132000
CONFIRM12_RELEASE = 132006


def _fresh_private_directory(path: Path) -> None:
    _private_directory(path)
    if any(path.iterdir()):
        raise ValueError("Stage145 output directories must be fresh and empty")


def _run_one(executable: Path, cue: Path, directory: Path, *, twelfth: bool, seconds: int) -> None:
    env = {
        "HOME": str(directory), "TMPDIR": str(directory), "PATH": os.defpath,
        "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
        "VH_SATURN_CAPTURE_GATE": str(directory / "gate"),
        "VH_SATURN_FAD_LOG": str(directory / "fad.vhcdlog"),
        "VH_SATURN_PRIVATE_FRAMES_DIR": str(directory),
        "VH_SATURN_START_AT_FRAME": "12060",
        "VH_SATURN_CONFIRM_AT_FRAME": "12240", "VH_SATURN_CONFIRM_BUTTON": "C",
        "VH_SATURN_CONFIRM_AT_FRAME2": "31200", "VH_SATURN_CONFIRM2_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME3": "36000", "VH_SATURN_CONFIRM3_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME4": "42000", "VH_SATURN_CONFIRM4_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME5": "48000", "VH_SATURN_CONFIRM5_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME6": "60000", "VH_SATURN_CONFIRM6_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME7": "72000", "VH_SATURN_CONFIRM7_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME8": "84000", "VH_SATURN_CONFIRM8_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME9": "96000", "VH_SATURN_CONFIRM9_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME10": str(CONFIRM10_PRESS),
        "VH_SATURN_CONFIRM10_ENABLED": "1",
        # Both cohorts share the tenth and eleventh C inputs.
        "VH_SATURN_CONFIRM_AT_FRAME11": str(CONFIRM11_PRESS),
        "VH_SATURN_CONFIRM11_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME12": str(CONFIRM12_PRESS),
        "VH_SATURN_CONFIRM12_ENABLED": "1" if twelfth else "0",
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
        raise ValueError("Stage145 private Yabause process timed out") from exc
    if status != 0:
        raise ValueError("Stage145 private Yabause process failed")
    if (directory / "gate").exists() or (directory / "gate").is_symlink():
        raise ValueError("Stage145 private CD capture gate remained open")


def _write_private_new(path: Path, content: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def run_private_prologue_continue_twelfth_c(
    cue: Path, track1: Path, track2: Path, executable: Path, expected_runner_sha256: str,
    control: Path, enabled: Path, report_path: Path,
    stage144_archive: Path, stage144_manifest: Path, stage144_audit_report: Path,
    stage144_checksums: Path, stage144_metadata_bundle: Path, stage144_drive_receipt: Path,
    *, seconds: int = MAX_SECONDS, pins: dict = PINNED,
) -> dict:
    """Run an isolated twelfth-C test only after Stage144's owner-only Drive gate passes."""
    if (type(seconds) is not int or seconds <= 0 or seconds > MAX_SECONDS or
            not isinstance(expected_runner_sha256, str) or not SHA256.fullmatch(expected_runner_sha256)):
        raise ValueError("Stage145 timeout or runner digest invalid")
    input_paths = (cue, track1, track2, executable, stage144_archive, stage144_manifest,
        stage144_audit_report, stage144_checksums, stage144_metadata_bundle, stage144_drive_receipt)
    for path in input_paths:
        if not path.is_absolute() or path.is_symlink():
            raise ValueError("Stage145 inputs must be absolute non-symlinked private paths")
        _not_in_checkout(path)
    if not report_path.is_absolute() or report_path.exists() or report_path.is_symlink():
        raise ValueError("Stage145 report path must be a fresh absolute path")
    _not_in_checkout(report_path)
    _private_directory(report_path.parent)
    _fresh_private_directory(control)
    _fresh_private_directory(enabled)
    if control.resolve() == enabled.resolve() or control.parent.resolve() != enabled.parent.resolve():
        raise ValueError("Stage145 cohorts must be distinct sibling directories")
    for output in (control, enabled):
        if (output.resolve() in report_path.resolve().parents or
                report_path.resolve() in output.resolve().parents):
            raise ValueError("Stage145 report cannot be inside or contain an output directory")
    for output in (control, enabled):
        for source in input_paths:
            if output.resolve() == source.resolve() or output.resolve() in source.resolve().parents or source.resolve() in output.resolve().parents:
                raise ValueError("Stage145 output/input paths overlap")

    stage144_integrity = verify_private_stage144_archive(
        stage144_archive, stage144_manifest, stage144_audit_report,
        stage144_checksums, stage144_metadata_bundle, stage144_drive_receipt,
    )
    before_media = _build_manifest(cue, track1, track2)
    _check_media(before_media, pins)
    runner_before = _fingerprint(executable)
    if runner_before[1] != expected_runner_sha256:
        raise ValueError("Stage145 executable does not match pinned Release runner digest")
    stage144_before = {path: _fingerprint(path) for path in input_paths[4:]}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = (
            pool.submit(_run_one, executable, cue, control, twelfth=False, seconds=seconds),
            pool.submit(_run_one, executable, cue, enabled, twelfth=True, seconds=seconds),
        )
        for future in futures:
            future.result()
    after_media = _build_manifest(cue, track1, track2)
    _check_media(after_media, pins)
    if before_media != after_media:
        raise ValueError("Stage145 original media changed during paired run")
    runner_after = _fingerprint(executable)
    if runner_after != runner_before or runner_after[1] != expected_runner_sha256:
        raise ValueError("Stage145 runner identity or digest changed during paired run")
    if any(_fingerprint(path) != fingerprint for path, fingerprint in stage144_before.items()):
        raise ValueError("Stage145 Stage144 predecessor evidence changed during paired run")
    stage144_integrity_after = verify_private_stage144_archive(
        stage144_archive, stage144_manifest, stage144_audit_report,
        stage144_checksums, stage144_metadata_bundle, stage144_drive_receipt,
    )
    if stage144_integrity_after != stage144_integrity:
        raise ValueError("Stage145 predecessor archive gate changed during paired run")
    audit = audit_private_prologue_continue_twelfth_c(control, enabled)
    report = {
        "schema": "vh-saturn-stage145-private-pair-run-1",
        "stage": 145,
        "run_exit_status": 0,
        "both_private_processes_returned_zero_status": True,
        "original_media_unchanged_before_after": True,
        "runner_unchanged_before_after": True,
        "runner_sha256_matches_pinned_release": True,
        "stage144_owner_only_drive_readback_gate": stage144_integrity,
        "stage144_drive_readback_receipt_verified": True,
        "paired_capture_audit": audit,
        "original_media_or_frame_hashes_exported": False,
        "full_playable_battle_or_unit_control_verified": False,
    }
    _write_private_new(report_path, (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    return {
        "stage": 145, "run_exit_status": 0, "frames_per_cohort": FRAME_COUNT,
        "pre_twelfth_checkpoint_pairs_equal": audit["pre_twelfth_checkpoint_equal_count"],
        "first_post_twelfth_divergence": audit["first_post_twelfth_framebuffer_divergence_by_133200"],
        "stage144_drive_readback_gate_passed": True,
        "original_media_unchanged": True, "runner_unchanged": True,
        "report_written": True, "full_playable_battle_or_unit_control_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cue", "track1", "track2", "executable", "control", "enabled", "report",
                 "stage144-archive", "stage144-manifest", "stage144-audit-report",
                 "stage144-checksums", "stage144-metadata-bundle", "stage144-drive-receipt"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--seconds", type=int, default=MAX_SECONDS)
    args = parser.parse_args()
    try:
        result = run_private_prologue_continue_twelfth_c(
            args.cue, args.track1, args.track2, args.executable, args.expected_runner_sha256,
            args.control, args.enabled, args.report, args.stage144_archive, args.stage144_manifest,
            args.stage144_audit_report, args.stage144_checksums, args.stage144_metadata_bundle,
            args.stage144_drive_receipt, seconds=args.seconds,
        )
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print("STAGE145_PRIVATE_PAIR_REJECTED", type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
