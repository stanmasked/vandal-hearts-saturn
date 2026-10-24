#!/usr/bin/env python3
"""Verify a Stage143 capture archive only after owner-only Drive readback.

The gate validates the archive, exact per-member manifest, separate audit report,
SHA256SUMS file, and a receipt tying all four files to owner-only Drive file IDs.
It never accepts a local-only archive as satisfying the storage policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile

from tools.saturn_private_capture_session import _not_in_checkout
from tools.saturn_private_original_start_sequence import SHA256

SCHEMA = "vh-saturn-stage143-private-capture-manifest-1"
RECEIPT_SCHEMA = "vh-saturn-stage143-drive-readback-receipt-1"
ARCHIVE_ROOT = "stage143-sourcepatched-full120000"
SIDEcars = {"fad.vhcdlog", "frames.stats", "pad-events.txt", "pad-state.txt",
            "post.png", "pre.png", "sh2-window.txt", "video-state.txt"}
MAX_ARCHIVE = 512 * 1024 * 1024
MAX_MANIFEST = 12 * 1024 * 1024
MAX_REPORT = 2 * 1024 * 1024
MAX_CHECKSUMS = 64 * 1024
MAX_RECEIPT = 64 * 1024


def _private_regular(path: Path, maximum: int, *, load_bytes: bool = True) -> tuple[os.stat_result, bytes]:
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("absolute non-symlinked private file required")
    _not_in_checkout(path)
    st = path.lstat()
    if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or
            stat.S_IMODE(st.st_mode) & 0o077 or st.st_size <= 0 or st.st_size > maximum):
        raise ValueError("unsafe, non-private, or oversized Stage143 evidence file")
    return st, path.read_bytes() if load_bytes else b""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _expected_names() -> set[str]:
    return {f"frame-{n}.png" for n in range(120, 120001, 120)} | SIDEcars


def _validate_cohort_items(items: object, cohort: str) -> dict[str, dict]:
    if not isinstance(items, list) or len(items) != 1008:
        raise ValueError("Stage143 manifest cohort must contain 1000 frames and eight sidecars")
    expected = _expected_names()
    result = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Stage143 manifest member is not an object")
        name, size, digest = item.get("name"), item.get("size_bytes"), item.get("sha256")
        if (not isinstance(name, str) or name not in expected or name in result or
                type(size) is not int or size <= 0 or size > 16_777_216 or
                not isinstance(digest, str) or not SHA256.fullmatch(digest)):
            raise ValueError("Stage143 manifest member name/size/hash invalid")
        result[name] = {"size_bytes": size, "sha256": digest}
    if set(result) != expected:
        raise ValueError("Stage143 manifest cohort member set differs from canonical layout")
    return result


def _verify_archive_members(archive: Path, manifest: dict) -> dict:
    if (manifest.get("schema") != SCHEMA or manifest.get("stage") != 143 or
            manifest.get("frames_per_cohort") != 1000 or
            manifest.get("archive_member_count") != 2016 or
            manifest.get("archive_contains_original_media") is not False or
            manifest.get("archive_contains_runner_binary") is not False):
        raise ValueError("Stage143 manifest schema or scope invalid")
    by_cohort = {
        "control": _validate_cohort_items(manifest.get("control_files"), "control"),
        "enabled": _validate_cohort_items(manifest.get("enabled_files"), "enabled"),
    }
    expected = {
        f"{ARCHIVE_ROOT}/{cohort}/{name}": item
        for cohort, items in by_cohort.items() for name, item in items.items()
    }
    seen = set()
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) != 2016:
            raise ValueError("Stage143 archive member count mismatch")
        for member in members:
            if (not member.isfile() or member.name not in expected or member.name in seen or
                    member.name.startswith("/") or "\\" in member.name or
                    any(part in ("", ".", "..") for part in member.name.split("/"))):
                raise ValueError("Stage143 archive contains unsafe or unexpected member")
            lowered = member.name.lower()
            if any(token in lowered for token in (".bin", ".cue", "yabause", "source/disc", "track 1", "track 2")):
                raise ValueError("Stage143 archive unexpectedly contains original media or runner")
            item = expected[member.name]
            if member.size != item["size_bytes"]:
                raise ValueError("Stage143 archive member size differs from manifest")
            stream = tar.extractfile(member)
            if stream is None:
                raise ValueError("Stage143 archive member cannot be read")
            h = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
            if h.hexdigest() != item["sha256"]:
                raise ValueError("Stage143 archive member SHA-256 differs from manifest")
            seen.add(member.name)
    if seen != set(expected):
        raise ValueError("Stage143 archive member set incomplete")
    return {"archive_member_count": len(seen), "cohorts": 2,
            "frames_per_cohort": 1000, "sidecars_per_cohort": 8,
            "original_media_in_archive": False, "runner_binary_in_archive": False,
            "all_member_hashes_match_manifest": True}


def _verify_legacy_private_stage143_archive(archive: Path, manifest_path: Path,
                                            audit_report_path: Path, checksums_path: Path,
                                            receipt_path: Path) -> dict:
    paths = (archive, manifest_path, audit_report_path, checksums_path, receipt_path)
    if len({p.resolve() for p in paths}) != len(paths):
        raise ValueError("Stage143 archive, manifest, report, checksums, and receipt must be distinct")
    stats = {}
    raw = {}
    limits = (MAX_ARCHIVE, MAX_MANIFEST, MAX_REPORT, MAX_CHECKSUMS, MAX_RECEIPT)
    for p, limit in zip(paths, limits):
        stats[p], raw[p] = _private_regular(p, limit, load_bytes=(p != archive))
    archive_sha, manifest_sha = _file_sha256(archive), _file_sha256(manifest_path)
    report_sha, checksums_sha = _file_sha256(audit_report_path), _file_sha256(checksums_path)
    try:
        manifest = json.loads(raw[manifest_path].decode("utf-8"))
        report = json.loads(raw[audit_report_path].decode("utf-8"))
        receipt = json.loads(raw[receipt_path].decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Stage143 manifest/report/receipt JSON invalid") from exc
    if (not isinstance(manifest, dict) or not isinstance(report, dict) or
            not isinstance(receipt, dict)):
        raise ValueError("Stage143 manifest/report/receipt must be JSON objects")
    if (manifest.get("archive_sha256") != archive_sha or
            manifest.get("archive_size_bytes") != stats[archive].st_size):
        raise ValueError("Stage143 archive fingerprint differs from manifest")
    if (report.get("archive_sha256") != archive_sha or
            report.get("archive_size_bytes") != stats[archive].st_size or
            report.get("archive_readback_and_member_sha256_verification_passed") is not True or
            report.get("run_exit_status") != 0 or
            report.get("both_private_processes_returned_zero_status") is not True):
        raise ValueError("Stage143 audit report does not attest a completed verified run")
    if (receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("stage") != 143 or
            receipt.get("owner_only") is not True or receipt.get("readback_verified") is not True):
        raise ValueError("Stage143 owner-only Drive readback receipt missing")
    ids = ("drive_file_id", "manifest_drive_file_id", "audit_report_drive_file_id",
           "checksums_drive_file_id")
    if any(not isinstance(receipt.get(k), str) or not receipt[k].strip() for k in ids):
        raise ValueError("Stage143 receipt lacks a Drive file ID for a required artifact")
    fingerprints = {
        "archive": (stats[archive].st_size, archive_sha),
        "manifest": (stats[manifest_path].st_size, manifest_sha),
        "audit_report": (stats[audit_report_path].st_size, report_sha),
        "checksums": (stats[checksums_path].st_size, checksums_sha),
    }
    for label, (size, digest) in fingerprints.items():
        if receipt.get(label + "_size_bytes") != size or receipt.get(label + "_sha256") != digest:
            raise ValueError("Stage143 receipt " + label + " fingerprint mismatch")
        if receipt.get(label + "_readback_sha256") != digest:
            raise ValueError("Stage143 Drive readback " + label + " SHA-256 mismatch")
    checksum_lines = raw[checksums_path].decode("ascii").splitlines()
    if len(checksum_lines) != 3:
        raise ValueError("Stage143 SHA256SUMS must contain exactly three entries")
    parsed = {}
    for line in checksum_lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._-]+)", line)
        if not match or match.group(2) in parsed:
            raise ValueError("Stage143 SHA256SUMS line invalid")
        parsed[match.group(2)] = match.group(1)
    expected_sums = {
        archive.name: archive_sha, manifest_path.name: manifest_sha,
        audit_report_path.name: report_sha,
    }
    if parsed != expected_sums:
        raise ValueError("Stage143 SHA256SUMS does not cover the exact archive/manifest/report")
    structural = _verify_archive_members(archive, manifest)
    return {
        "schema": "vh-saturn-stage143-drive-readback-gate-1",
        "stage143_owner_only_drive_readback_verified": True,
        "archive_size_bytes": stats[archive].st_size, "archive_sha256": archive_sha,
        "manifest_size_bytes": stats[manifest_path].st_size, "manifest_sha256": manifest_sha,
        "audit_report_size_bytes": stats[audit_report_path].st_size, "audit_report_sha256": report_sha,
        "checksums_size_bytes": stats[checksums_path].st_size, "checksums_sha256": checksums_sha,
        **structural,
    }



RAW_SCHEMA = "vh-saturn-stage143-raw-capture-manifest-1"
RAW_RECEIPT_SCHEMA = "vh-saturn-stage143-drive-readback-receipt-2"
RAW_ARCHIVE_NAME = "stage143-full120000-raw-captures.tar.gz"
RAW_MANIFEST_NAME = "stage143-full120000-raw-manifest.json"
RAW_REPORT_NAME = "stage143-full-pair-audit.json"
RAW_BUNDLE_NAME = "stage143-full120000-metadata-bundle.tar.gz"
RAW_BUNDLE_MEMBERS = {
    "manifest/" + RAW_MANIFEST_NAME,
    "reports/" + RAW_REPORT_NAME,
    "checksums/" + RAW_ARCHIVE_NAME + ".sha256",
    "checksums/" + RAW_MANIFEST_NAME + ".sha256",
    "checksums/" + RAW_REPORT_NAME + ".sha256",
    "README.txt",
}
MAX_BUNDLE = 16 * 1024 * 1024


def _expected_raw_names() -> set[str]:
    frames = {f"frame-{n}.png" for n in range(120, 120001, 120)}
    return {f"{cohort}/{name}" for cohort in ("control", "enabled")
            for name in (frames | SIDEcars)}


def _validate_raw_manifest(manifest: dict, archive: Path) -> dict[str, dict]:
    if (manifest.get("schema") != RAW_SCHEMA or manifest.get("stage") != 143
            or manifest.get("experiment") != "source-patched-release-full-120000-paired-run"
            or manifest.get("archive_file_name") != archive.name
            or manifest.get("raw_member_count") != 2016
            or manifest.get("cohorts") != {"control": 1000, "enabled": 1000}
            or manifest.get("contains_original_disc_media") is not False
            or manifest.get("contains_derived_audit_report") is not False
            or manifest.get("contains_runner_binary", False) is not False):
        raise ValueError("Stage143 raw manifest schema or scope invalid")
    items = manifest.get("members")
    expected_names = _expected_raw_names()
    if not isinstance(items, list) or len(items) != 2016:
        raise ValueError("Stage143 raw manifest must list exactly 2016 members")
    expected = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Stage143 raw manifest member is not an object")
        name, size, digest = item.get("path"), item.get("size_bytes"), item.get("sha256")
        if (not isinstance(name, str) or name not in expected_names or name in expected
                or type(size) is not int or size <= 0 or size > 16_777_216
                or not isinstance(digest, str) or not SHA256.fullmatch(digest)):
            raise ValueError("Stage143 raw manifest member path/size/hash invalid")
        expected[name] = {"size_bytes": size, "sha256": digest}
    if set(expected) != expected_names:
        raise ValueError("Stage143 raw manifest member set differs from canonical layout")
    if type(manifest.get("raw_payload_bytes")) is not int or sum(
        x["size_bytes"] for x in expected.values()
    ) != manifest["raw_payload_bytes"]:
        raise ValueError("Stage143 raw manifest payload byte total mismatch")
    return expected


def _verify_raw_archive_members(archive: Path, manifest: dict) -> dict:
    expected = _validate_raw_manifest(manifest, archive)
    seen = set()
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) != 2016:
            raise ValueError("Stage143 raw archive member count mismatch")
        for member in members:
            name = member.name
            if (not member.isfile() or name not in expected or name in seen
                    or name.startswith("/") or "\\" in name
                    or any(part in ("", ".", "..") for part in name.split("/"))):
                raise ValueError("Stage143 raw archive contains unsafe or unexpected member")
            lowered = name.lower()
            if any(token in lowered for token in (
                ".bin", ".cue", ".iso", ".rom", ".elf", "yabause",
                "source/disc", "track 1", "track 2", "original-media",
            )):
                raise ValueError("Stage143 raw archive unexpectedly contains original media or runner")
            item = expected[name]
            if member.size != item["size_bytes"]:
                raise ValueError("Stage143 raw archive member size differs from manifest")
            stream = tar.extractfile(member)
            if stream is None:
                raise ValueError("Stage143 raw archive member cannot be read")
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
            if digest.hexdigest() != item["sha256"]:
                raise ValueError("Stage143 raw archive member SHA-256 differs from manifest")
            seen.add(name)
    if seen != set(expected):
        raise ValueError("Stage143 raw archive member set incomplete")
    return {
        "archive_member_count": len(seen),
        "cohorts": 2,
        "frames_per_cohort": 1000,
        "sidecars_per_cohort": 8,
        "raw_payload_bytes": manifest["raw_payload_bytes"],
        "original_media_in_archive": False,
        "runner_binary_in_archive": False,
        "all_member_hashes_match_manifest": True,
    }


def _bundle_files(bundle_path: Path) -> dict[str, bytes]:
    found = {}
    with tarfile.open(bundle_path, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) != len(RAW_BUNDLE_MEMBERS):
            raise ValueError("Stage143 metadata bundle member count mismatch")
        for member in members:
            name = member.name
            if (not member.isfile() or name not in RAW_BUNDLE_MEMBERS or name in found
                    or name.startswith("/") or "\\" in name
                    or any(part in ("", ".", "..") for part in name.split("/"))
                    or member.size <= 0 or member.size > MAX_MANIFEST):
                raise ValueError("Stage143 metadata bundle contains unsafe or unexpected member")
            stream = tar.extractfile(member)
            if stream is None:
                raise ValueError("Stage143 metadata bundle member cannot be read")
            data = stream.read(member.size + 1)
            if len(data) != member.size:
                raise ValueError("Stage143 metadata bundle member size mismatch")
            found[name] = data
    if set(found) != RAW_BUNDLE_MEMBERS:
        raise ValueError("Stage143 metadata bundle member set incomplete")
    return found


def _verify_raw_bundle_sidecar(bundle_files: dict[str, bytes], filename: str, digest: str) -> None:
    member = "checksums/" + filename + ".sha256"
    try:
        lines = bundle_files[member].decode("ascii").splitlines()
    except (KeyError, UnicodeError) as exc:
        raise ValueError("Stage143 metadata bundle checksum sidecar unreadable") from exc
    if len(lines) != 1:
        raise ValueError("Stage143 metadata bundle checksum sidecar must contain one line")
    match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", lines[0])
    if not match or match.group(1) != digest:
        raise ValueError("Stage143 metadata bundle checksum sidecar digest mismatch")
    listed = match.group(2)
    parts = PurePosixPath(listed).parts
    if ("\\" in listed or PurePosixPath(listed).name != filename
            or any(part in ("", ".", "..") for part in parts)):
        raise ValueError("Stage143 metadata bundle checksum sidecar path invalid")


def _verify_raw_stage143_drive_readback(
    archive: Path, manifest_path: Path, audit_report_path: Path,
    metadata_bundle_path: Path, receipt_path: Path,
) -> dict:
    paths = (archive, manifest_path, audit_report_path, metadata_bundle_path, receipt_path)
    if len({p.resolve() for p in paths}) != len(paths):
        raise ValueError("Stage143 archive, manifest, report, bundle, and receipt must be distinct")
    limits = (MAX_ARCHIVE, MAX_MANIFEST, MAX_REPORT, MAX_BUNDLE, MAX_RECEIPT)
    stats, raw = {}, {}
    for path, limit in zip(paths, limits):
        stats[path], raw[path] = _private_regular(path, limit, load_bytes=(path != archive))
    archive_sha = _file_sha256(archive)
    manifest_sha = _file_sha256(manifest_path)
    report_sha = _file_sha256(audit_report_path)
    bundle_sha = _file_sha256(metadata_bundle_path)
    try:
        manifest = json.loads(raw[manifest_path].decode("utf-8"))
        report = json.loads(raw[audit_report_path].decode("utf-8"))
        receipt = json.loads(raw[receipt_path].decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Stage143 raw manifest/report/readback receipt JSON invalid") from exc
    if not isinstance(manifest, dict) or not isinstance(report, dict) or not isinstance(receipt, dict):
        raise ValueError("Stage143 raw manifest/report/readback receipt must be JSON objects")
    if (manifest.get("archive_sha256") != archive_sha
            or manifest.get("archive_size_bytes") != stats[archive].st_size):
        raise ValueError("Stage143 raw archive fingerprint differs from manifest")
    if (report.get("schema") != "vh-saturn-stage143-full-pair-audit-1"
            or report.get("kind") != "STAGE143_FULL_PRIVATE_PAIR_AUDIT"
            or report.get("stage") != 143
            or report.get("paired_cold_boot_processes") != 2
            or report.get("frames_per_process") != 120000
            or report.get("checkpoint_png_count_per_process") != 1000
            or report.get("all_pngs_decoded_and_crc_validated") is not True
            or report.get("all_pad_receipts_and_diagnostic_sequences_verified") is not True
            or report.get("source_media_and_runner_unchanged_per_controller_receipt") is not True
            or report.get("tenth_c_effect_on_original_framebuffer_confirmed") is not True
            or report.get("first_post_tenth_framebuffer_divergence") != 108120
            or report.get("pre_tenth_checkpoint_pairs_identical") != 899
            or report.get("post_tenth_checkpoint_pairs_different") != 100
            or report.get("first_battle_or_player_control_verified") is not False
            or report.get("original_media_or_frame_hashes_exported") is not False):
        raise ValueError("Stage143 aggregate audit report does not attest the verified paired run")
    if (receipt.get("schema") != RAW_RECEIPT_SCHEMA or receipt.get("stage") != 143
            or receipt.get("owner_only") is not True
            or receipt.get("readback_verified") is not True
            or receipt.get("archive_shared") is not False
            or receipt.get("metadata_bundle_shared") is not False):
        raise ValueError("Stage143 owner-only Drive readback receipt missing")
    ids = ("drive_file_id", "metadata_bundle_drive_file_id", "private_folder_id",
           "archive_parent_folder_id", "metadata_bundle_parent_folder_id")
    if any(not isinstance(receipt.get(key), str) or not receipt[key].strip() for key in ids):
        raise ValueError("Stage143 receipt lacks Drive IDs or private folder provenance")
    if (receipt["private_folder_id"] != receipt["archive_parent_folder_id"]
            or receipt["private_folder_id"] != receipt["metadata_bundle_parent_folder_id"]):
        raise ValueError("Stage143 archive and metadata bundle are not in the same private folder")
    fingerprints = {
        "archive": (stats[archive].st_size, archive_sha),
        "manifest": (stats[manifest_path].st_size, manifest_sha),
        "audit_report": (stats[audit_report_path].st_size, report_sha),
        "metadata_bundle": (stats[metadata_bundle_path].st_size, bundle_sha),
    }
    for label, (size, digest) in fingerprints.items():
        if receipt.get(label + "_size_bytes") != size or receipt.get(label + "_sha256") != digest:
            raise ValueError("Stage143 receipt " + label + " fingerprint mismatch")
        if receipt.get(label + "_readback_sha256") != digest:
            raise ValueError("Stage143 Drive readback " + label + " SHA-256 mismatch")
    if (archive.name != RAW_ARCHIVE_NAME or metadata_bundle_path.name != RAW_BUNDLE_NAME
            or manifest_path.name != RAW_MANIFEST_NAME or audit_report_path.name != RAW_REPORT_NAME):
        raise ValueError("Stage143 raw readback filenames differ from canonical names")
    bundle_files = _bundle_files(metadata_bundle_path)
    if (bundle_files["manifest/" + RAW_MANIFEST_NAME] != raw[manifest_path]
            or bundle_files["reports/" + RAW_REPORT_NAME] != raw[audit_report_path]):
        raise ValueError("Stage143 metadata bundle differs from the separately extracted manifest/report")
    _verify_raw_bundle_sidecar(bundle_files, RAW_ARCHIVE_NAME, archive_sha)
    _verify_raw_bundle_sidecar(bundle_files, RAW_MANIFEST_NAME, manifest_sha)
    _verify_raw_bundle_sidecar(bundle_files, RAW_REPORT_NAME, report_sha)
    try:
        readme = bundle_files["README.txt"].decode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Stage143 metadata bundle README encoding invalid") from exc
    for token in (
        "Drive file ID: " + receipt["drive_file_id"],
        "Archive size: " + str(stats[archive].st_size),
        "Archive SHA-256: " + archive_sha,
        "independent Drive download/readback matched that size and SHA-256",
    ):
        if token not in readme:
            raise ValueError("Stage143 metadata bundle README provenance mismatch")
    structural = _verify_raw_archive_members(archive, manifest)
    return {
        "schema": "vh-saturn-stage143-drive-readback-gate-2",
        "stage143_owner_only_drive_readback_verified": True,
        "archive_drive_file_id": receipt["drive_file_id"],
        "metadata_bundle_drive_file_id": receipt["metadata_bundle_drive_file_id"],
        "archive_size_bytes": stats[archive].st_size,
        "archive_sha256": archive_sha,
        "manifest_size_bytes": stats[manifest_path].st_size,
        "manifest_sha256": manifest_sha,
        "audit_report_size_bytes": stats[audit_report_path].st_size,
        "audit_report_sha256": report_sha,
        "metadata_bundle_size_bytes": stats[metadata_bundle_path].st_size,
        "metadata_bundle_sha256": bundle_sha,
        **structural,
    }


def verify_private_stage143_archive(archive: Path, manifest_path: Path,
                                    audit_report_path: Path, checksums_path: Path,
                                    receipt_path: Path) -> dict:
    """Verify either the legacy Stage143 bundle or the current raw archive + metadata bundle."""
    try:
        _, manifest_bytes = _private_regular(manifest_path, MAX_MANIFEST)
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        return _verify_legacy_private_stage143_archive(
            archive, manifest_path, audit_report_path, checksums_path, receipt_path
        )
    if isinstance(manifest, dict) and manifest.get("schema") == RAW_SCHEMA:
        return _verify_raw_stage143_drive_readback(
            archive, manifest_path, audit_report_path, checksums_path, receipt_path
        )
    return _verify_legacy_private_stage143_archive(
        archive, manifest_path, audit_report_path, checksums_path, receipt_path
    )

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("archive", "manifest", "audit-report", "receipt"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--checksums", "--metadata-bundle", dest="checksums", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = verify_private_stage143_archive(args.archive, args.manifest,
            args.audit_report, args.checksums, args.receipt)
    except (OSError, ValueError, TypeError, tarfile.TarError):
        print("STAGE143_DRIVE_READBACK_GATE_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
