#!/usr/bin/env python3
"""Stage149: run four original-disc paired controls on ONE private host.

Invokes the existing pinned Stage144/145 private pair runners sequentially,
giving 8 cold-boot Yabause processes in 4 independent, fully audited pairs.
All captures stay within a fresh, owner-only private directory. A successful
matrix is evidence of a finished experiment, NOT of deterministic gameplay
or first battle control. This code is never run on ROM-free public CI.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys

from tools.saturn_private_capture_cohort import _private_directory, _private_regular
from tools.saturn_private_stage150_storage_guard import assert_durable_private_workspace
from tools.saturn_private_capture_session import _fingerprint, _not_in_checkout, PINNED
from tools.saturn_private_original_start_pair import _build_manifest, _check_media
from tools.saturn_private_prologue_continue_eleventh_c import (
    run_private_prologue_continue_eleventh_c as _run144, MAX_SECONDS as SECONDS144,
)
from tools.saturn_private_prologue_continue_twelfth_c import (
    run_private_prologue_continue_twelfth_c as _run145, MAX_SECONDS as SECONDS145,
)
from tools.saturn_private_stage147_replay_matrix import audit_private_stage147_replay_matrix as _matrix

SCHEDULE = (("stage144_a", 144), ("stage145_a", 145),
            ("stage144_b", 144), ("stage145_b", 145))
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
SOURCE_KEYS = (
    "cue", "track1", "track2", "stage144_executable", "stage145_executable",
    "stage124_drive_receipt", "stage124_drive_readback_archive",
    "stage143_archive", "stage143_manifest", "stage143_audit_report",
    "stage143_metadata_bundle", "stage143_drive_receipt",
    "stage144_archive", "stage144_manifest", "stage144_audit_report",
    "stage144_checksums", "stage144_metadata_bundle", "stage144_drive_receipt",
)


def _write_new(path: Path, data: dict) -> None:
    content = (json.dumps(data, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _preflight(args) -> dict:
    root = args.output_root
    if (not isinstance(root, Path) or not root.is_absolute() or root.is_symlink()
            or root != root.resolve()):
        raise ValueError("Stage149 output root must be an absolute canonical private directory")
    _not_in_checkout(root)
    _private_directory(root)
    if any(root.iterdir()):
        raise ValueError("Stage149 output root must be completely empty (never resume or overwrite)")
    if (type(args.seconds) is not int or args.seconds <= 0 or
            args.seconds > min(SECONDS144, SECONDS145)):
        raise ValueError("Stage149 requested per-pair timeout outside permitted range")
    paths = {key: getattr(args, key) for key in SOURCE_KEYS}
    for key, path in paths.items():
        if not isinstance(path, Path) or not path.is_absolute() or path.is_symlink():
            raise ValueError("Stage149 requires absolute, non-symlinked private sources")
        _not_in_checkout(path)
        if path.resolve() == root or root in path.resolve().parents or path.resolve() in root.parents:
            raise ValueError("Stage149 source and output trees overlap")
    # Reject ephemeral overlays, CI runners and insecure local volumes before
    # touching original media or creating any capture artifacts.
    assert_durable_private_workspace(root, tuple(paths.values()))
    if args.stage144_executable.resolve() == args.stage145_executable.resolve():
        raise ValueError("Stage149 requires distinct Stage144/145 runner files")
    if not all(isinstance(getattr(args, key), str) and
               SHA256.fullmatch(getattr(args, key))
               for key in ("stage144_runner_sha256", "stage145_runner_sha256")):
        raise ValueError("Stage149 expected runner SHA-256 pins malformed")
    if args.stage144_runner_sha256 == args.stage145_runner_sha256:
        raise ValueError("Stage149 runner versions must use distinct pinned digests")
    source_fingerprints = {key: _fingerprint(path) for key, path in paths.items()}
    if (source_fingerprints["stage144_executable"][1] != args.stage144_runner_sha256 or
            source_fingerprints["stage145_executable"][1] != args.stage145_runner_sha256):
        raise ValueError("Stage149 runner SHA-256 does not match provided pinned release")
    manifest = _build_manifest(args.cue, args.track1, args.track2)
    _check_media(manifest, PINNED)
    return source_fingerprints


def _recheck(args, original: dict) -> None:
    # Fail closed if the mounted private volume changes or becomes unsafe.
    assert_durable_private_workspace(
        args.output_root, tuple(getattr(args, key) for key in SOURCE_KEYS))
    for key in SOURCE_KEYS:
        if _fingerprint(getattr(args, key)) != original[key]:
            raise ValueError("Stage149 private source or executable changed between paired runs")
    _check_media(_build_manifest(args.cue, args.track1, args.track2), PINNED)


def _verify_report(path: Path, stage: int) -> None:
    raw = _private_regular(path, 2 * 1024 * 1024)
    try:
        report = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Stage149 pair report unreadable") from exc
    if (not isinstance(report, dict) or
            report.get("schema") != f"vh-saturn-stage{stage}-private-pair-run-1" or
            report.get("stage") != stage or report.get("run_exit_status") != 0 or
            report.get("both_private_processes_returned_zero_status") is not True or
            report.get("runner_sha256_matches_pinned_release") is not True or
            report.get("original_media_unchanged_before_after") is not True or
            report.get("runner_unchanged_before_after") is not True or
            report.get("original_media_or_frame_hashes_exported") is not False or
            report.get("full_playable_battle_or_unit_control_verified") is not False or
            not isinstance(report.get("paired_capture_audit"), dict)):
        raise ValueError("Stage149 Stage144/145 pair runner report failed integrity contract")
    if stage == 144:
        valid = (report.get("stage124_drive_readback_receipt_verified") is True and
                 report.get("stage143_drive_readback_receipt_verified") is True and
                 isinstance(report.get("stage143_owner_only_drive_readback_gate"), dict))
    else:
        valid = (report.get("stage144_drive_readback_receipt_verified") is True and
                 isinstance(report.get("stage144_owner_only_drive_readback_gate"), dict))
    if not valid:
        raise ValueError("Stage149 owner-only predecessor readback gate missing")


def run_private_stage149(args, *, run144=_run144, run145=_run145, matrix=_matrix) -> dict:
    initial = _preflight(args)
    root = args.output_root
    reports = root / "reports"
    reports.mkdir(mode=0o700)
    _private_directory(reports)
    controls: dict[str, Path] = {}
    # Explicit interleaving reduces confusion between elapsed-time drift and
    # build-specific drift. Four paired experiments = eight cold boots total.
    for label, stage in SCHEDULE:
        _recheck(args, initial)
        control = root / (label + "_control")
        enabled = root / (label + "_enabled")
        control.mkdir(mode=0o700)
        enabled.mkdir(mode=0o700)
        report = reports / (label + ".json")
        common = (
            args.cue, args.track1, args.track2,
            args.stage144_executable if stage == 144 else args.stage145_executable,
            args.stage144_runner_sha256 if stage == 144 else args.stage145_runner_sha256,
            control, enabled, report,
        )
        if stage == 144:
            result = run144(
                *common,
                args.stage124_drive_receipt, args.stage124_drive_readback_archive,
                args.stage143_archive, args.stage143_manifest,
                args.stage143_audit_report, args.stage143_metadata_bundle,
                args.stage143_drive_receipt,
                seconds=args.seconds,
            )
        else:
            result = run145(
                *common,
                args.stage144_archive, args.stage144_manifest,
                args.stage144_audit_report, args.stage144_checksums,
                args.stage144_metadata_bundle, args.stage144_drive_receipt,
                seconds=args.seconds,
            )
        if (not isinstance(result, dict) or result.get("stage") != stage or
                result.get("run_exit_status") != 0 or result.get("report_written") is not True):
            raise ValueError("Stage149 paired runner did not complete successfully")
        _verify_report(report, stage)
        _recheck(args, initial)
        controls[label] = control

    summary = matrix(tuple(controls[label] for label in
                           ("stage144_a", "stage144_b", "stage145_a", "stage145_b")))
    if (not isinstance(summary, dict) or
            summary.get("schema") != "vh-saturn-stage147-four-control-replay-matrix-1" or
            summary.get("checkpoint_count") != 800 or
            summary.get("original_media_or_frame_hashes_exported") is not False or
            summary.get("battle_or_tactical_player_control_verified") is not False):
        raise ValueError("Stage149 four-control comparator did not satisfy privacy contract")
    _recheck(args, initial)
    output = {
        "schema": "vh-saturn-stage149-private-four-pair-replay-sequence-1",
        "experiment_completed": True,
        "sequential_same_driver_process": True,
        "sequential_paired_experiments": 4,
        "total_separate_yabause_cold_boots": 8,
        "stage144_paired_experiments": 2,
        "stage145_paired_experiments": 2,
        "media_and_both_runners_unchanged_across_all_pairs": True,
        "private_persistent_filesystem_preflight_passed": True,
        "runner_hashes_match_separately_supplied_pins": True,
        "all_predecessor_owner_only_receipts_verified_by_pair_runners": True,
        "comparison": summary,
        "owner_only_drive_upload_and_independent_readback_verified": False,
        "original_media_or_frame_hashes_exported": False,
        "fresh_gameplay_battle_control_verified": False,
    }
    _write_new(reports / "stage149-summary.json", output)
    return {
        "schema": output["schema"], "experiment_completed": True,
        "compared_checkpoints": 800, "classification": summary.get("classification"),
        "drive_readback_verified": False, "battle_control_verified": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for key in SOURCE_KEYS:
        p.add_argument("--" + key.replace("_", "-"), required=True, type=Path)
    p.add_argument("--stage144-runner-sha256", required=True)
    p.add_argument("--stage145-runner-sha256", required=True)
    p.add_argument("--output-root", required=True, type=Path)
    p.add_argument("--seconds", type=int, default=min(SECONDS144, SECONDS145))
    args = p.parse_args()
    try:
        summary = run_private_stage149(args)
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print("STAGE149_PRIVATE_REPLAY_REJECTED", type(exc).__name__, str(exc),
              file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
