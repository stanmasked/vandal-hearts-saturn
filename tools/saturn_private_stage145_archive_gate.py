"""Stage145 raw-capture archive gate; requires independent owner-only Drive readback."""
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

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
RAW_SCHEMA = "vh-saturn-stage145-raw-capture-manifest-1"
RECEIPT_SCHEMA = "vh-saturn-stage145-drive-readback-receipt-1"
ARCHIVE_NAME = "stage145-full144000-raw-captures.tar.gz"
MANIFEST_NAME = "stage145-full144000-raw-manifest.json"
REPORT_NAME = "stage145-full-pair-audit.json"
CHECKSUMS_NAME = "stage145-full144000-SHA256SUMS"
BUNDLE_NAME = "stage145-full144000-metadata-bundle.tar.gz"
FRAME_COUNT = 144000
CHECKPOINTS = tuple(range(120, FRAME_COUNT + 1, 120))
FRAMES_PER_COHORT = len(CHECKPOINTS)
RAW_MEMBER_COUNT = 2 * (FRAMES_PER_COHORT + 8)
SIDECARS = frozenset(("fad.vhcdlog", "frames.stats", "pad-events.txt", "pad-state.txt",
                      "post.png", "pre.png", "sh2-window.txt", "video-state.txt"))
BUNDLE_MEMBERS = {
    "manifest/" + MANIFEST_NAME,
    "reports/" + REPORT_NAME,
    "checksums/" + ARCHIVE_NAME + ".sha256",
    "checksums/" + MANIFEST_NAME + ".sha256",
    "checksums/" + REPORT_NAME + ".sha256",
    "README.txt",
}
MAX_ARCHIVE = 768 * 1024 * 1024
MAX_MANIFEST = 16 * 1024 * 1024
MAX_REPORT = 2 * 1024 * 1024
MAX_CHECKSUMS = 64 * 1024
MAX_BUNDLE = 16 * 1024 * 1024
MAX_RECEIPT = 128 * 1024


def _private_regular(path: Path, maximum: int, *, load_bytes: bool = True):
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("absolute non-symlinked private file required")
    _not_in_checkout(path)
    st = path.lstat()
    if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1
            or stat.S_IMODE(st.st_mode) & 0o077
            or st.st_size <= 0 or st.st_size > maximum):
        raise ValueError("unsafe, non-private, or oversized Stage145 evidence file")
    return st, path.read_bytes() if load_bytes else b""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _expected_member_paths() -> set[str]:
    filenames = {f"frame-{n}.png" for n in CHECKPOINTS} | set(SIDECARS)
    return {f"{cohort}/{name}" for cohort in ("control", "enabled") for name in filenames}


def _validate_manifest(manifest: dict, archive: Path) -> dict[str, dict]:
    expected_paths = _expected_member_paths()
    if (manifest.get("schema") != RAW_SCHEMA or manifest.get("stage") != 145
            or manifest.get("experiment") != "source-patched-release-full-144000-frame-twelfth-C-paired-run"
            or manifest.get("archive_file_name") != archive.name
            or manifest.get("raw_member_count") != RAW_MEMBER_COUNT
            or manifest.get("cohorts") != {"control": FRAMES_PER_COHORT, "enabled": FRAMES_PER_COHORT}
            or manifest.get("contains_original_disc_media") is not False
            or manifest.get("contains_derived_audit_report") is not False
            or manifest.get("contains_runner_binary", False) is not False):
        raise ValueError("Stage145 raw manifest schema or scope invalid")
    items = manifest.get("members")
    if not isinstance(items, list) or len(items) != RAW_MEMBER_COUNT:
        raise ValueError("Stage145 raw manifest must list exactly 2416 members")
    expected = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Stage145 raw manifest member is not an object")
        name, size, digest = item.get("path"), item.get("size_bytes"), item.get("sha256")
        if (not isinstance(name, str) or name not in expected_paths or name in expected
                or type(size) is not int or size <= 0 or size > 16_777_216
                or not isinstance(digest, str) or not SHA256.fullmatch(digest)):
            raise ValueError("Stage145 raw manifest member path/size/hash invalid")
        expected[name] = {"size_bytes": size, "sha256": digest}
    if set(expected) != expected_paths:
        raise ValueError("Stage145 raw manifest member set differs from canonical layout")
    if (type(manifest.get("raw_payload_bytes")) is not int
            or sum(x["size_bytes"] for x in expected.values()) != manifest["raw_payload_bytes"]):
        raise ValueError("Stage145 raw manifest payload byte total mismatch")
    return expected


def _verify_archive_members(archive: Path, manifest: dict) -> dict:
    expected = _validate_manifest(manifest, archive)
    seen = set()
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) != RAW_MEMBER_COUNT:
            raise ValueError("Stage145 raw archive member count mismatch")
        for member in members:
            name = member.name
            if (not member.isfile() or name not in expected or name in seen
                    or name.startswith("/") or "\\" in name
                    or any(part in ("", ".", "..") for part in name.split("/"))):
                raise ValueError("Stage145 raw archive contains unsafe or unexpected member")
            lowered = name.lower()
            if any(token in lowered for token in (
                ".bin", ".cue", ".iso", ".rom", ".elf", "yabause",
                "source/disc", "track 1", "track 2", "original-media",
            )):
                raise ValueError("Stage145 raw archive unexpectedly contains original media or runner")
            item = expected[name]
            if member.size != item["size_bytes"]:
                raise ValueError("Stage145 raw archive member size differs from manifest")
            stream = tar.extractfile(member)
            if stream is None:
                raise ValueError("Stage145 raw archive member cannot be read")
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
            if digest.hexdigest() != item["sha256"]:
                raise ValueError("Stage145 raw archive member SHA-256 differs from manifest")
            seen.add(name)
    if seen != set(expected):
        raise ValueError("Stage145 raw archive member set incomplete")
    return {
        "archive_member_count": len(seen),
        "cohorts": 2,
        "frames_per_cohort": FRAMES_PER_COHORT,
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
        if len(members) != len(BUNDLE_MEMBERS):
            raise ValueError("Stage145 metadata bundle member count mismatch")
        for member in members:
            name = member.name
            if (not member.isfile() or name not in BUNDLE_MEMBERS or name in found
                    or name.startswith("/") or "\\" in name
                    or any(part in ("", ".", "..") for part in name.split("/"))
                    or member.size <= 0 or member.size > MAX_MANIFEST):
                raise ValueError("Stage145 metadata bundle contains unsafe or unexpected member")
            stream = tar.extractfile(member)
            if stream is None:
                raise ValueError("Stage145 metadata bundle member cannot be read")
            data = stream.read(member.size + 1)
            if len(data) != member.size:
                raise ValueError("Stage145 metadata bundle member size mismatch")
            found[name] = data
    if set(found) != BUNDLE_MEMBERS:
        raise ValueError("Stage145 metadata bundle member set incomplete")
    return found


def _verify_bundle_sidecar(bundle_files: dict[str, bytes], filename: str, digest: str) -> None:
    try:
        lines = bundle_files["checksums/" + filename + ".sha256"].decode("ascii").splitlines()
    except (KeyError, UnicodeError) as exc:
        raise ValueError("Stage145 metadata bundle checksum sidecar unreadable") from exc
    if len(lines) != 1:
        raise ValueError("Stage145 metadata bundle checksum sidecar must contain one line")
    match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", lines[0])
    if not match or match.group(1) != digest:
        raise ValueError("Stage145 metadata bundle checksum sidecar digest mismatch")
    listed = match.group(2)
    parts = PurePosixPath(listed).parts
    if ("\\" in listed or PurePosixPath(listed).name != filename
            or any(part in ("", ".", "..") for part in parts)):
        raise ValueError("Stage145 metadata bundle checksum sidecar path invalid")


def _verify_standalone_checksums(raw: bytes, expected: dict[str, str]) -> None:
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise ValueError("Stage145 standalone checksums encoding invalid") from exc
    if len(lines) != 3:
        raise ValueError("Stage145 standalone checksums must contain exactly three lines")
    found = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        if not match:
            raise ValueError("Stage145 standalone checksum line malformed")
        digest, name = match.groups()
        if name in found:
            raise ValueError("Stage145 standalone checksum filename duplicated")
        found[name] = digest
    if found != expected:
        raise ValueError("Stage145 standalone checksums do not match exact artifacts")


def verify_private_stage145_archive(
    archive: Path, manifest_path: Path, audit_report_path: Path,
    checksums_path: Path, metadata_bundle_path: Path, receipt_path: Path,
) -> dict:
    paths = (archive, manifest_path, audit_report_path, checksums_path, metadata_bundle_path, receipt_path)
    if len({p.resolve() for p in paths}) != len(paths):
        raise ValueError("Stage145 archive, manifest, report, checksums, bundle, and receipt must be distinct")
    limits = (MAX_ARCHIVE, MAX_MANIFEST, MAX_REPORT, MAX_CHECKSUMS, MAX_BUNDLE, MAX_RECEIPT)
    stats, raw = {}, {}
    for path, limit in zip(paths, limits):
        stats[path], raw[path] = _private_regular(path, limit, load_bytes=(path != archive))
    archive_sha = _file_sha256(archive)
    manifest_sha = _file_sha256(manifest_path)
    report_sha = _file_sha256(audit_report_path)
    checksums_sha = _file_sha256(checksums_path)
    bundle_sha = _file_sha256(metadata_bundle_path)
    try:
        manifest = json.loads(raw[manifest_path].decode("utf-8"))
        report = json.loads(raw[audit_report_path].decode("utf-8"))
        receipt = json.loads(raw[receipt_path].decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Stage145 manifest/report/readback receipt JSON invalid") from exc
    if not all(isinstance(x, dict) for x in (manifest, report, receipt)):
        raise ValueError("Stage145 manifest/report/readback receipt must be JSON objects")
    if (manifest.get("archive_sha256") != archive_sha
            or manifest.get("archive_size_bytes") != stats[archive].st_size):
        raise ValueError("Stage145 raw archive fingerprint differs from manifest")
    nested = report.get("paired_capture_audit")
    divergence = report.get("first_post_twelfth_framebuffer_divergence")
    if (report.get("schema") != "vh-saturn-stage145-full-pair-audit-1"
            or report.get("kind") != "STAGE145_FULL_PRIVATE_PAIR_AUDIT"
            or report.get("stage") != 145
            or report.get("paired_cold_boot_processes") != 2
            or report.get("frames_per_process") != FRAME_COUNT
            or report.get("checkpoint_png_count_per_process") != FRAMES_PER_COHORT
            or report.get("all_pngs_decoded_and_crc_validated") is not True
            or report.get("all_pad_receipts_and_diagnostic_sequences_verified") is not True
            or report.get("source_media_and_runner_unchanged_before_after") is not True
            or report.get("stage144_drive_readback_receipt_verified") is not True
            or not isinstance(report.get("stage144_owner_only_drive_readback_gate"), dict)
            or report["stage144_owner_only_drive_readback_gate"].get("stage144_owner_only_drive_readback_verified") is not True
            or report.get("twelfth_c_effect_on_original_framebuffer_confirmed") is not True
            or type(divergence) is not int or divergence not in range(132120, 133201, 120)
            or report.get("pre_twelfth_checkpoint_pairs_identical") != 1099
            or report.get("frame_144000_differs") is not True
            or report.get("first_battle_or_player_control_verified") is not False
            or report.get("original_media_or_frame_hashes_exported") is not False
            or not isinstance(nested, dict)
            or nested.get("all_checkpoint_pngs_and_diagnostic_sequences_verified") is not True
            or nested.get("pre_twelfth_checkpoint_equal_count") != 1099
            or nested.get("twelfth_C_press_frame") != 132000
            or nested.get("twelfth_C_release_frame") != 132006
            or nested.get("shared_eleventh_C_press_frame") != 120000
            or nested.get("shared_eleventh_C_release_frame") != 120006
            or nested.get("shared_tenth_C_press_frame") != 108000
            or nested.get("shared_tenth_C_release_frame") != 108006
            or nested.get("pre_twelfth_checkpoint_total") != 1099
            or nested.get("checkpoint_png_count_per_process") != 1200
            or nested.get("same_dimensions_across_runs") is not True
            or nested.get("cd_logs_differ") is not False
            or nested.get("control_cd_event_count") != nested.get("intervention_cd_event_count")
            or nested.get("first_post_twelfth_framebuffer_divergence_by_133200") != divergence
            or nested.get("first_post_twelfth_framebuffer_divergence_through_144000") != divergence
            or nested.get("frame_144000_differs") is not True
            or nested.get("first_battle_or_player_control_verified") is not False
            or nested.get("original_media_or_frame_hashes_exported") is not False):
        raise ValueError("Stage145 aggregate audit report does not attest the verified paired run")
    if (receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("stage") != 145
            or receipt.get("owner_only") is not True
            or receipt.get("readback_verified") is not True
            or receipt.get("archive_shared") is not False
            or receipt.get("metadata_bundle_shared") is not False
            or receipt.get("manifest_shared") is not False
            or receipt.get("audit_report_shared") is not False
            or receipt.get("checksums_shared") is not False):
        raise ValueError("Stage145 owner-only Drive readback receipt missing")
    ids = (
        "drive_file_id", "metadata_bundle_drive_file_id", "manifest_drive_file_id",
        "audit_report_drive_file_id", "checksums_drive_file_id", "private_folder_id",
        "archive_parent_folder_id", "metadata_bundle_parent_folder_id",
        "manifest_parent_folder_id", "audit_report_parent_folder_id", "checksums_parent_folder_id",
    )
    if any(not isinstance(receipt.get(key), str) or not receipt[key].strip() for key in ids):
        raise ValueError("Stage145 receipt lacks Drive IDs or private folder provenance")
    folder = receipt["private_folder_id"]
    if any(receipt[key] != folder for key in (
        "archive_parent_folder_id", "metadata_bundle_parent_folder_id", "manifest_parent_folder_id",
        "audit_report_parent_folder_id", "checksums_parent_folder_id",
    )):
        raise ValueError("Stage145 artifacts are not in the same private Drive folder")
    fingerprints = {
        "archive": (stats[archive].st_size, archive_sha),
        "manifest": (stats[manifest_path].st_size, manifest_sha),
        "audit_report": (stats[audit_report_path].st_size, report_sha),
        "checksums": (stats[checksums_path].st_size, checksums_sha),
        "metadata_bundle": (stats[metadata_bundle_path].st_size, bundle_sha),
    }
    for label, (size, digest) in fingerprints.items():
        if receipt.get(label + "_size_bytes") != size or receipt.get(label + "_sha256") != digest:
            raise ValueError("Stage145 receipt " + label + " fingerprint mismatch")
        if receipt.get(label + "_readback_sha256") != digest:
            raise ValueError("Stage145 Drive readback " + label + " SHA-256 mismatch")
    if (archive.name != ARCHIVE_NAME or manifest_path.name != MANIFEST_NAME
            or audit_report_path.name != REPORT_NAME or checksums_path.name != CHECKSUMS_NAME
            or metadata_bundle_path.name != BUNDLE_NAME):
        raise ValueError("Stage145 raw readback filenames differ from canonical names")
    _verify_standalone_checksums(raw[checksums_path], {
        ARCHIVE_NAME: archive_sha, MANIFEST_NAME: manifest_sha, REPORT_NAME: report_sha,
    })
    bundle_files = _bundle_files(metadata_bundle_path)
    if (bundle_files["manifest/" + MANIFEST_NAME] != raw[manifest_path]
            or bundle_files["reports/" + REPORT_NAME] != raw[audit_report_path]):
        raise ValueError("Stage145 metadata bundle differs from separate manifest/report")
    _verify_bundle_sidecar(bundle_files, ARCHIVE_NAME, archive_sha)
    _verify_bundle_sidecar(bundle_files, MANIFEST_NAME, manifest_sha)
    _verify_bundle_sidecar(bundle_files, REPORT_NAME, report_sha)
    try:
        readme = bundle_files["README.txt"].decode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Stage145 metadata bundle README encoding invalid") from exc
    for token in (
        "Drive file ID: " + receipt["drive_file_id"],
        "Archive size: " + str(stats[archive].st_size),
        "Archive SHA-256: " + archive_sha,
        "independent Drive download/readback matched that size and SHA-256",
    ):
        if token not in readme:
            raise ValueError("Stage145 metadata bundle README provenance mismatch")
    structural = _verify_archive_members(archive, manifest)
    return {
        "schema": "vh-saturn-stage145-drive-readback-gate-1",
        "stage145_owner_only_drive_readback_verified": True,
        "archive_drive_file_id": receipt["drive_file_id"],
        "metadata_bundle_drive_file_id": receipt["metadata_bundle_drive_file_id"],
        "archive_size_bytes": stats[archive].st_size,
        "archive_sha256": archive_sha,
        "manifest_size_bytes": stats[manifest_path].st_size,
        "manifest_sha256": manifest_sha,
        "audit_report_size_bytes": stats[audit_report_path].st_size,
        "audit_report_sha256": report_sha,
        "checksums_size_bytes": stats[checksums_path].st_size,
        "checksums_sha256": checksums_sha,
        "metadata_bundle_size_bytes": stats[metadata_bundle_path].st_size,
        "metadata_bundle_sha256": bundle_sha,
        **structural,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("archive", "manifest", "audit-report", "checksums", "metadata-bundle", "receipt"):
        parser.add_argument("--" + flag, type=Path, required=True)
    args = parser.parse_args()
    try:
        report = verify_private_stage145_archive(
            args.archive, args.manifest, args.audit_report, args.checksums,
            args.metadata_bundle, args.receipt,
        )
    except (OSError, ValueError, TypeError, tarfile.TarError):
        print("STAGE145_DRIVE_READBACK_GATE_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
