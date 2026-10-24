#!/usr/bin/env python3
"""Package audited Stage145 captures and metadata for owner-only Drive readback.

This tool never uploads files, reads original disc media, or writes to the public
checkout. Upload and independent readback are separate explicit steps.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile

from tools.saturn_private_capture_cohort import _private_directory, _private_regular
from tools.saturn_private_capture_session import _not_in_checkout
from tools.saturn_private_prologue_continue_twelfth_c_audit import (
    CHECKPOINTS, audit_private_prologue_continue_twelfth_c,
)
from tools.saturn_private_stage145_archive_gate import (
    ARCHIVE_NAME, BUNDLE_NAME, CHECKSUMS_NAME, MANIFEST_NAME, REPORT_NAME,
    SIDECARS, RAW_SCHEMA, RECEIPT_SCHEMA, BUNDLE_MEMBERS, MAX_ARCHIVE,
    MAX_MANIFEST, MAX_REPORT, MAX_CHECKSUMS, MAX_BUNDLE, MAX_RECEIPT,
    verify_private_stage145_archive,
)

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
FRAME_COUNT = 144000
EXPERIMENT = "source-patched-release-full-144000-frame-twelfth-C-paired-run"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _write_new_private(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink() or not path.parent.is_dir():
        raise ValueError("Stage145 output must be a fresh file in an existing private directory")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _validate_output_dir(path: Path) -> None:
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("Stage145 package output must be an absolute nonsymlinked directory")
    _not_in_checkout(path)
    _private_directory(path)


def _capture_inventory(control: Path, enabled: Path) -> tuple[list[dict], int]:
    expected_frames = {f"frame-{n}.png" for n in CHECKPOINTS}
    expected_names = expected_frames | set(SIDECARS)
    members: list[dict] = []
    total = 0
    for cohort_name, directory in (("control", control), ("enabled", enabled)):
        if not directory.is_absolute() or directory.is_symlink():
            raise ValueError("Stage145 capture paths must be absolute nonsymlinked directories")
        _not_in_checkout(directory)
        _private_directory(directory)
        if {p.name for p in directory.iterdir()} != expected_names:
            raise ValueError("Stage145 raw capture file set incomplete or unexpected")
        for name in sorted(expected_names):
            path = directory / name
            st = path.lstat()
            if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or
                    stat.S_IMODE(st.st_mode) & 0o077 or st.st_size <= 0 or st.st_size > 16_777_216):
                raise ValueError("Stage145 capture member is unsafe, non-private, or oversized")
            digest = _sha256(path)
            members.append({"path": f"{cohort_name}/{name}", "size_bytes": st.st_size, "sha256": digest})
            total += st.st_size
    members.sort(key=lambda x: x["path"])
    if len(members) != 2416:
        raise ValueError("Stage145 raw inventory must contain exactly 2,416 members")
    return members, total


def _verify_runner_report(report_path: Path, control: Path, enabled: Path) -> tuple[dict, dict]:
    raw = _private_regular(report_path, MAX_REPORT)
    try:
        runner_report = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Stage145 runner report is not valid UTF-8 JSON") from exc
    if (not isinstance(runner_report, dict) or
            runner_report.get("schema") != "vh-saturn-stage145-private-pair-run-1" or
            runner_report.get("stage") != 145 or runner_report.get("run_exit_status") != 0 or
            runner_report.get("both_private_processes_returned_zero_status") is not True or
            runner_report.get("original_media_unchanged_before_after") is not True or
            runner_report.get("runner_unchanged_before_after") is not True or
            runner_report.get("runner_sha256_matches_pinned_release") is not True or
            runner_report.get("stage144_drive_readback_receipt_verified") is not True or
            runner_report.get("original_media_or_frame_hashes_exported") is not False or
            runner_report.get("full_playable_battle_or_unit_control_verified") is not False):
        raise ValueError("Stage145 runner report does not attest a completed, integrity-only pair")
    predecessor = runner_report.get("stage144_owner_only_drive_readback_gate")
    if not isinstance(predecessor, dict) or predecessor.get("stage144_owner_only_drive_readback_verified") is not True:
        raise ValueError("Stage145 requires verified Stage144 owner-only Drive readback")
    audit = audit_private_prologue_continue_twelfth_c(control, enabled)
    if runner_report.get("paired_capture_audit") != audit:
        raise ValueError("Stage145 runner report differs from independent raw-capture audit")
    if (audit.get("frames_per_process") != FRAME_COUNT or
            audit.get("checkpoint_png_count_per_process") != len(CHECKPOINTS) or
            audit.get("pre_twelfth_checkpoint_equal_count") != 1099 or
            audit.get("first_battle_or_player_control_verified") is not False or
            audit.get("original_media_or_frame_hashes_exported") is not False):
        raise ValueError("Stage145 independent pair audit did not satisfy the evidence contract")
    return runner_report, audit


def _tar_add_bytes(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o600
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    import io
    tar.addfile(info, io.BytesIO(data))


def build_raw_package(control: Path, enabled: Path, runner_report_path: Path, output_dir: Path) -> dict:
    """Create the raw capture archive, canonical manifest, audit report and SHA256SUMS."""
    _validate_output_dir(output_dir)
    for p in (control, enabled, runner_report_path):
        if not p.is_absolute() or p.is_symlink():
            raise ValueError("Stage145 inputs must be absolute nonsymlinked private paths")
        _not_in_checkout(p)
    if output_dir.resolve() in control.resolve().parents or control.resolve() in output_dir.resolve().parents or output_dir.resolve() in enabled.resolve().parents or enabled.resolve() in output_dir.resolve().parents:
        raise ValueError("Stage145 package output overlaps capture inputs")
    runner_report, audit = _verify_runner_report(runner_report_path, control, enabled)
    members, payload_bytes = _capture_inventory(control, enabled)
    archive = output_dir / ARCHIVE_NAME
    manifest_path = output_dir / MANIFEST_NAME
    report_path = output_dir / REPORT_NAME
    checksums_path = output_dir / CHECKSUMS_NAME
    if any(p.exists() or p.is_symlink() for p in (archive, manifest_path, report_path, checksums_path)):
        raise ValueError("Stage145 package outputs must all be fresh")

    fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as sink:
            with gzip.GzipFile(filename="", fileobj=sink, mode="wb", mtime=0) as gz:
                with tarfile.open(fileobj=gz, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                    for cohort_name, directory in (("control", control), ("enabled", enabled)):
                        for item in members:
                            if not item["path"].startswith(cohort_name + "/"):
                                continue
                            name = item["path"].split("/", 1)[1]
                            source = directory / name
                            before = source.lstat()
                            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or stat.S_IMODE(before.st_mode) & 0o077:
                                raise ValueError("Stage145 source member changed before packaging")
                            with source.open("rb") as stream:
                                data = stream.read(16_777_217)
                            if len(data) != item["size_bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                                raise ValueError("Stage145 source member changed during packaging")
                            _tar_add_bytes(tar, item["path"], data)
            sink.flush()
            os.fsync(sink.fileno())
    except BaseException:
        archive.unlink(missing_ok=True)
        raise

    archive_size = archive.stat().st_size
    archive_sha = _sha256(archive)
    manifest = {
        "schema": RAW_SCHEMA,
        "stage": 145,
        "experiment": EXPERIMENT,
        "archive_file_name": ARCHIVE_NAME,
        "archive_size_bytes": archive_size,
        "archive_sha256": archive_sha,
        "raw_member_count": len(members),
        "cohorts": {"control": len(CHECKPOINTS), "enabled": len(CHECKPOINTS)},
        "raw_payload_bytes": payload_bytes,
        "contains_original_disc_media": False,
        "contains_derived_audit_report": False,
        "contains_runner_binary": False,
        "members": members,
    }
    nested = audit
    divergence = nested["first_post_twelfth_framebuffer_divergence_by_133200"]
    full_report = {
        "schema": "vh-saturn-stage145-full-pair-audit-1",
        "kind": "STAGE145_FULL_PRIVATE_PAIR_AUDIT",
        "stage": 145,
        "paired_cold_boot_processes": 2,
        "frames_per_process": FRAME_COUNT,
        "checkpoint_png_count_per_process": len(CHECKPOINTS),
        "all_pngs_decoded_and_crc_validated": True,
        "all_pad_receipts_and_diagnostic_sequences_verified": True,
        "source_media_and_runner_unchanged_before_after": True,
        "stage144_drive_readback_receipt_verified": True,
        "stage144_owner_only_drive_readback_gate": runner_report["stage144_owner_only_drive_readback_gate"],
        "twelfth_c_effect_on_original_framebuffer_confirmed": True,
        "first_post_twelfth_framebuffer_divergence": divergence,
        "pre_twelfth_checkpoint_pairs_identical": nested["pre_twelfth_checkpoint_equal_count"],
        "frame_144000_differs": nested["frame_144000_differs"],
        "first_battle_or_player_control_verified": False,
        "original_media_or_frame_hashes_exported": False,
        "paired_capture_audit": nested,
    }
    _write_new_private(manifest_path, (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode())
    _write_new_private(report_path, (json.dumps(full_report, sort_keys=True, indent=2) + "\n").encode())
    checksums = "".join(f"{_sha256(p)}  {p.name}\n" for p in (archive, manifest_path, report_path)).encode("ascii")
    _write_new_private(checksums_path, checksums)
    return {
        "stage": 145, "archive": str(archive), "archive_size_bytes": archive_size,
        "archive_sha256": archive_sha, "manifest": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path), "audit_report": str(report_path),
        "audit_report_sha256": _sha256(report_path), "checksums": str(checksums_path),
        "checksums_sha256": _sha256(checksums_path), "raw_member_count": len(members),
        "frames_per_cohort": len(CHECKPOINTS), "independent_pair_audit_passed": True,
        "owner_only_drive_readback_still_required": True,
    }


def build_metadata_bundle(output_dir: Path, *, archive_drive_file_id: str,
                          archive_readback_size_bytes: int, archive_readback_sha256: str) -> dict:
    """Build the metadata bundle after archive upload and independent readback."""
    _validate_output_dir(output_dir)
    if (not isinstance(archive_drive_file_id, str) or not archive_drive_file_id.strip() or
            type(archive_readback_size_bytes) is not int or archive_readback_size_bytes <= 0 or
            not isinstance(archive_readback_sha256, str) or not SHA256.fullmatch(archive_readback_sha256)):
        raise ValueError("Stage145 archive Drive readback receipt inputs invalid")
    archive = output_dir / ARCHIVE_NAME
    manifest_path = output_dir / MANIFEST_NAME
    report_path = output_dir / REPORT_NAME
    checksums_path = output_dir / CHECKSUMS_NAME
    for path, limit in ((archive, MAX_ARCHIVE), (manifest_path, MAX_MANIFEST), (report_path, MAX_REPORT), (checksums_path, MAX_CHECKSUMS)):
        _private_regular(path, limit)
    archive_size = archive.stat().st_size
    archive_sha = _sha256(archive)
    if archive_size != archive_readback_size_bytes or archive_sha != archive_readback_sha256:
        raise ValueError("Stage145 archive Drive readback does not match local archive")
    manifest_bytes = manifest_path.read_bytes()
    report_bytes = report_path.read_bytes()
    checksum_lines = checksums_path.read_text("ascii").splitlines()
    if len(checksum_lines) != 3:
        raise ValueError("Stage145 standalone checksum list malformed")
    expected = {
        ARCHIVE_NAME: archive_sha,
        MANIFEST_NAME: _sha256(manifest_path),
        REPORT_NAME: _sha256(report_path),
    }
    found = {}
    for line in checksum_lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        if not match or match.group(2) in found:
            raise ValueError("Stage145 standalone checksum list malformed")
        found[match.group(2)] = match.group(1)
    if found != expected:
        raise ValueError("Stage145 standalone checksums do not match artifacts")
    bundle = output_dir / BUNDLE_NAME
    if bundle.exists() or bundle.is_symlink():
        raise ValueError("Stage145 metadata bundle must be a fresh file")
    readme = (
        "Vandal Hearts Saturn — Stage145 private capture evidence\n"
        "Access: owner-only Google Drive. Original disc media and runner binaries are excluded.\n"
        f"Drive file ID: {archive_drive_file_id}\n"
        f"Archive size: {archive_size}\n"
        f"Archive SHA-256: {archive_sha}\n"
        "The archive was independently downloaded from Drive after upload; independent Drive download/readback matched that size and SHA-256.\n"
        "The separate raw manifest records every archive member size and SHA-256. The aggregate report includes the independently rerun pair audit.\n"
        "The paired experiment verifies dialogue/framebuffer progression only; it does not establish battle entry or tactical player control.\n"
    ).encode("utf-8")
    archive_sidecar = f"{archive_sha}  {ARCHIVE_NAME}\n".encode("ascii")
    manifest_sidecar = f"{expected[MANIFEST_NAME]}  {MANIFEST_NAME}\n".encode("ascii")
    report_sidecar = f"{expected[REPORT_NAME]}  {REPORT_NAME}\n".encode("ascii")
    fd = os.open(bundle, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as sink:
            with gzip.GzipFile(filename="", fileobj=sink, mode="wb", mtime=0) as gz:
                with tarfile.open(fileobj=gz, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                    for name, data in (
                        ("manifest/" + MANIFEST_NAME, manifest_bytes),
                        ("reports/" + REPORT_NAME, report_bytes),
                        ("checksums/" + ARCHIVE_NAME + ".sha256", archive_sidecar),
                        ("checksums/" + MANIFEST_NAME + ".sha256", manifest_sidecar),
                        ("checksums/" + REPORT_NAME + ".sha256", report_sidecar),
                        ("README.txt", readme),
                    ):
                        _tar_add_bytes(tar, name, data)
            sink.flush()
            os.fsync(sink.fileno())
    except BaseException:
        bundle.unlink(missing_ok=True)
        raise
    if bundle.stat().st_size > MAX_BUNDLE:
        bundle.unlink(missing_ok=True)
        raise ValueError("Stage145 metadata bundle exceeds size limit")
    return {"metadata_bundle": str(bundle), "size_bytes": bundle.stat().st_size,
            "sha256": _sha256(bundle), "contains_original_disc_media": False}


def build_receipt(output_dir: Path, receipt: dict) -> Path:
    """Write the final receipt only after all five Drive artifacts were read back."""
    _validate_output_dir(output_dir)
    if not isinstance(receipt, dict):
        raise ValueError("Stage145 receipt input must be a JSON object")
    receipt = dict(receipt)
    receipt["schema"] = RECEIPT_SCHEMA
    receipt["stage"] = 145
    receipt["owner_only"] = True
    receipt["readback_verified"] = True
    for key in ("archive_shared", "metadata_bundle_shared", "manifest_shared", "audit_report_shared", "checksums_shared"):
        receipt[key] = False
    required = (
        "drive_file_id", "metadata_bundle_drive_file_id", "manifest_drive_file_id",
        "audit_report_drive_file_id", "checksums_drive_file_id", "private_folder_id",
        "archive_parent_folder_id", "metadata_bundle_parent_folder_id", "manifest_parent_folder_id",
        "audit_report_parent_folder_id", "checksums_parent_folder_id",
    )
    if any(not isinstance(receipt.get(k), str) or not receipt[k].strip() for k in required):
        raise ValueError("Stage145 receipt missing Drive IDs or private folder provenance")
    if any(receipt[k] != receipt["private_folder_id"] for k in (
        "archive_parent_folder_id", "metadata_bundle_parent_folder_id", "manifest_parent_folder_id",
        "audit_report_parent_folder_id", "checksums_parent_folder_id")):
        raise ValueError("Stage145 artifacts must share one private parent folder")
    for label in ("archive", "metadata_bundle", "manifest", "audit_report", "checksums"):
        size = receipt.get(label + "_size_bytes")
        digest = receipt.get(label + "_sha256")
        readback = receipt.get(label + "_readback_sha256")
        if type(size) is not int or size <= 0 or not isinstance(digest, str) or not SHA256.fullmatch(digest) or readback != digest:
            raise ValueError("Stage145 receipt fingerprints/readback values invalid")
    path = output_dir / "stage145-drive-readback-receipt.json"
    _write_new_private(path, (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    raw = sub.add_parser("raw")
    for key in ("control", "enabled", "runner-report", "output-dir"):
        raw.add_argument("--" + key, type=Path, required=True)
    bundle = sub.add_parser("bundle")
    bundle.add_argument("--output-dir", type=Path, required=True)
    bundle.add_argument("--archive-drive-file-id", required=True)
    bundle.add_argument("--archive-readback-size-bytes", type=int, required=True)
    bundle.add_argument("--archive-readback-sha256", required=True)
    args = parser.parse_args()
    try:
        if args.command == "raw":
            result = build_raw_package(args.control, args.enabled, args.runner_report, args.output_dir)
        else:
            result = build_metadata_bundle(args.output_dir, archive_drive_file_id=args.archive_drive_file_id,
                archive_readback_size_bytes=args.archive_readback_size_bytes,
                archive_readback_sha256=args.archive_readback_sha256)
    except (OSError, ValueError, TypeError, tarfile.TarError) as exc:
        print("STAGE145_CAPTURE_PACKAGING_REJECTED", type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
