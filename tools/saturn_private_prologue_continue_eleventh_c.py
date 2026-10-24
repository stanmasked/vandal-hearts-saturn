#!/usr/bin/env python3
"""Stage144 private paired runner; refuses to run without verified Stage143 Drive readback."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
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
from tools.saturn_private_original_start_sequence import MAX_SECONDS, SHA256
from tools.saturn_private_prologue_continue_tenth_c import (
    _require_stage124_drive_readback_receipt, _enforce_stage124_capture_archive_integrity,
)
from tools.saturn_private_stage143_archive_gate import verify_private_stage143_archive
from tools.saturn_private_prologue_continue_eleventh_c_audit import audit_private_prologue_continue_eleventh_c

FRAME_COUNT = 132000
CONFIRM10_PRESS = 108000
CONFIRM10_RELEASE = 108006
CONFIRM11_PRESS = 120000
CONFIRM11_RELEASE = 120006


def _fresh_private_directory(path: Path) -> None:
    _private_directory(path)
    if any(path.iterdir()):
        raise ValueError("Stage144 output directories must be fresh and empty")


def _run_one(executable: Path, cue: Path, directory: Path, *, eleventh: bool, seconds: int) -> None:
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
        # The tenth C is deliberately enabled in BOTH cohorts.
        "VH_SATURN_CONFIRM_AT_FRAME10": str(CONFIRM10_PRESS),
        "VH_SATURN_CONFIRM10_ENABLED": "1",
        "VH_SATURN_CONFIRM_AT_FRAME11": str(CONFIRM11_PRESS),
        "VH_SATURN_CONFIRM11_ENABLED": "1" if eleventh else "0",
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
        raise ValueError("Stage144 private Yabause process timed out") from exc
    if status != 0:
        raise ValueError("Stage144 private Yabause process failed")
    if (directory / "gate").exists() or (directory / "gate").is_symlink():
        raise ValueError("Stage144 private CD capture gate remained open")


def _write_private_new(path: Path, content: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def run_private_prologue_continue_eleventh_c(
    cue: Path, track1: Path, track2: Path, executable: Path, expected_runner_sha256: str,
    control: Path, enabled: Path, report_path: Path,
    stage124_drive_receipt: Path, stage124_drive_readback_archive: Path,
    stage143_archive: Path, stage143_manifest: Path, stage143_audit_report: Path,
    stage143_metadata_bundle: Path, stage143_drive_receipt: Path,
    *, seconds: int = MAX_SECONDS, pins: dict = PINNED,
) -> dict:
    """Run the next C input only after Stage143's complete owner-only Drive readback gate passes."""
    if (type(seconds) is not int or seconds <= 0 or seconds > MAX_SECONDS or
            not isinstance(expected_runner_sha256, str) or not SHA256.fullmatch(expected_runner_sha256)):
        raise ValueError("Stage144 timeout or runner digest invalid")
    input_paths = (cue, track1, track2, executable, stage124_drive_receipt,
        stage124_drive_readback_archive, stage143_archive, stage143_manifest,
        stage143_audit_report, stage143_metadata_bundle, stage143_drive_receipt)
    for path in input_paths:
        if not path.is_absolute() or path.is_symlink():
            raise ValueError("Stage144 inputs must be absolute non-symlinked private paths")
        _not_in_checkout(path)
    if not report_path.is_absolute() or report_path.exists() or report_path.is_symlink():
        raise ValueError("Stage144 report path must be a fresh absolute path")
    _not_in_checkout(report_path)
    _private_directory(report_path.parent)
    _fresh_private_directory(control)
    _fresh_private_directory(enabled)
    if control.resolve() == enabled.resolve() or control.parent.resolve() != enabled.parent.resolve():
        raise ValueError("Stage144 cohorts must be distinct sibling directories")
    for output in (control, enabled):
        if (output.resolve() in report_path.resolve().parents or
                report_path.resolve() in output.resolve().parents):
            raise ValueError("Stage144 report cannot be inside or contain an output directory")
    for output in (control, enabled):
        for source in input_paths:
            if output.resolve() == source.resolve() or output.resolve() in source.resolve().parents or source.resolve() in output.resolve().parents:
                raise ValueError("Stage144 output/input paths overlap")

    # Mandatory predecessor receipts: both the original Stage124 archive and
    # the complete Stage143 raw capture, exact manifest, report and checksums
    # must have owner-only Drive IDs plus verified readback SHA-256 values.
    stage124_fingerprint = _require_stage124_drive_readback_receipt(stage124_drive_receipt, stage124_drive_readback_archive)
    stage124_integrity = _enforce_stage124_capture_archive_integrity(stage124_drive_readback_archive, stage124_fingerprint)
    stage143_integrity = verify_private_stage143_archive(
        stage143_archive, stage143_manifest, stage143_audit_report,
        stage143_metadata_bundle, stage143_drive_receipt,
    )

    before_manifest = _build_manifest(cue, track1, track2)
    _check_media(before_manifest, pins)
    runner_before = _fingerprint(executable)
    if runner_before[1] != expected_runner_sha256:
        raise ValueError("Stage144 executable does not match pinned Release runner digest")
    stage124_before = _fingerprint(stage124_drive_readback_archive)
    stage143_before = _fingerprint(stage143_archive)
    stage143_manifest_before = _fingerprint(stage143_manifest)
    stage143_report_before = _fingerprint(stage143_audit_report)
    stage143_metadata_bundle_before = _fingerprint(stage143_metadata_bundle)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = (
            pool.submit(_run_one, executable, cue, control, eleventh=False, seconds=seconds),
            pool.submit(_run_one, executable, cue, enabled, eleventh=True, seconds=seconds),
        )
        for future in futures:
            future.result()
    after_manifest = _build_manifest(cue, track1, track2)
    _check_media(after_manifest, pins)
    if before_manifest != after_manifest:
        raise ValueError("Stage144 original media changed during paired run")
    runner_after = _fingerprint(executable)
    if runner_after != runner_before or runner_after[1] != expected_runner_sha256:
        raise ValueError("Stage144 runner identity or digest changed during paired run")
    if _fingerprint(stage124_drive_readback_archive) != stage124_before:
        raise ValueError("Stage144 Stage124 archive changed during paired run")
    if (_fingerprint(stage143_archive) != stage143_before or
            _fingerprint(stage143_manifest) != stage143_manifest_before or
            _fingerprint(stage143_audit_report) != stage143_report_before or
            _fingerprint(stage143_metadata_bundle) != stage143_metadata_bundle_before):
        raise ValueError("Stage144 Stage143 predecessor evidence changed during paired run")
    # Re-run the owner-only Drive readback gate after emulation as well.
    stage143_integrity_after = verify_private_stage143_archive(
        stage143_archive, stage143_manifest, stage143_audit_report,
        stage143_metadata_bundle, stage143_drive_receipt,
    )
    if stage143_integrity_after != stage143_integrity:
        raise ValueError("Stage144 predecessor archive gate changed during paired run")
    audit = audit_private_prologue_continue_eleventh_c(control, enabled)
    report = {
        "schema": "vh-saturn-stage144-private-pair-run-1",
        "stage": 144,
        "run_exit_status": 0,
        "both_private_processes_returned_zero_status": True,
        "original_media_unchanged_before_after": True,
        "runner_unchanged_before_after": True,
        "runner_sha256_matches_pinned_release": True,
        "stage124_archive_integrity_gate": stage124_integrity,
        "stage143_owner_only_drive_readback_gate": stage143_integrity,
        "paired_capture_audit": audit,
        "original_media_or_frame_hashes_exported": False,
        "full_playable_battle_or_unit_control_verified": False,
    }
    _write_private_new(report_path, (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    return {
        "stage": 144, "run_exit_status": 0, "frames_per_cohort": FRAME_COUNT,
        "pre_eleventh_checkpoint_pairs_equal": audit["pre_eleventh_checkpoint_equal_count"],
        "first_post_eleventh_divergence": audit["first_post_eleventh_framebuffer_divergence_by_121200"],
        "stage143_drive_readback_gate_passed": True,
        "original_media_unchanged": True, "runner_unchanged": True,
        "report_written": True, "full_playable_battle_or_unit_control_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cue", "track1", "track2", "executable", "control", "enabled", "report",
                 "stage124-drive-receipt", "stage124-drive-readback-archive",
                 "stage143-archive", "stage143-manifest", "stage143-audit-report",
                 "stage143-drive-receipt"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--stage143-metadata-bundle", "--stage143-checksums", dest="stage143_metadata_bundle", type=Path, required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--seconds", type=int, default=MAX_SECONDS)
    args = parser.parse_args()
    try:
        result = run_private_prologue_continue_eleventh_c(
            args.cue, args.track1, args.track2, args.executable, args.expected_runner_sha256,
            args.control, args.enabled, args.report, args.stage124_drive_receipt,
            args.stage124_drive_readback_archive, args.stage143_archive, args.stage143_manifest,
            args.stage143_audit_report, args.stage143_metadata_bundle, args.stage143_drive_receipt,
            seconds=args.seconds,
        )
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print("STAGE144_PRIVATE_PAIR_REJECTED", type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
