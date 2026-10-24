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
from pathlib import Path
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


def _private_regular(path: Path, maximum: int) -> tuple[os.stat_result, bytes]:
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("absolute non-symlinked private file required")
    _not_in_checkout(path)
    st = path.lstat()
    if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or
            stat.S_IMODE(st.st_mode) & 0o077 or st.st_size <= 0 or st.st_size > maximum):
        raise ValueError("unsafe, non-private, or oversized Stage143 evidence file")
    return st, path.read_bytes()


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


def verify_private_stage143_archive(archive: Path, manifest_path: Path,
                                    audit_report_path: Path, checksums_path: Path,
                                    receipt_path: Path) -> dict:
    paths = (archive, manifest_path, audit_report_path, checksums_path, receipt_path)
    if len({p.resolve() for p in paths}) != len(paths):
        raise ValueError("Stage143 archive, manifest, report, checksums, and receipt must be distinct")
    stats = {}
    raw = {}
    limits = (MAX_ARCHIVE, MAX_MANIFEST, MAX_REPORT, MAX_CHECKSUMS, MAX_RECEIPT)
    for p, limit in zip(paths, limits):
        stats[p], raw[p] = _private_regular(p, limit)
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("archive", "manifest", "audit-report", "checksums", "receipt"):
        parser.add_argument("--" + flag, type=Path, required=True)
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
