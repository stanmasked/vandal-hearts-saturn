"""Synthetic-only Stage143 archive gate tests; no game media is used."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest

from tools.saturn_private_stage143_archive_gate import verify_private_stage143_archive, _expected_names

ARCHIVE_NAME = "stage143-sourcepatched-full120000-private.tar.gz"
MANIFEST_NAME = "stage143-sourcepatched-full120000-manifest.json"
REPORT_NAME = "stage143-sourcepatched-full120000-audit.json"
SUMS_NAME = "stage143-sourcepatched-full120000-SHA256SUMS"
RECEIPT_NAME = "stage143-drive-readback-receipt.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build_fixture(root: Path):
    names = sorted(_expected_names(), key=lambda n: (0, int(n[6:-4])) if n.startswith("frame-") else (1, n))
    cohorts = {"control": [], "enabled": []}
    payloads = {}
    for cohort in ("control", "enabled"):
        for name in names:
            data = b"x" if name.startswith("frame-") else b"s"
            cohorts[cohort].append({"name": name, "size_bytes": len(data), "sha256": digest(data)})
            payloads[f"stage143-sourcepatched-full120000/{cohort}/{name}"] = data
    archive = root / ARCHIVE_NAME
    with archive.open("xb") as raw:
        os.chmod(archive, 0o600)
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                for name, data in sorted(payloads.items()):
                    info = tarfile.TarInfo(name)
                    info.size = len(data); info.mode = 0o600; info.mtime = 0; info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    import io
                    tar.addfile(info, io.BytesIO(data))
        raw.flush(); os.fsync(raw.fileno())
    archive_bytes = archive.read_bytes()
    manifest = {
        "schema": "vh-saturn-stage143-private-capture-manifest-1",
        "stage": 143, "frames_per_cohort": 1000, "archive_member_count": 2016,
        "archive_contains_original_media": False, "archive_contains_runner_binary": False,
        "archive_size_bytes": len(archive_bytes), "archive_sha256": digest(archive_bytes),
        "control_files": cohorts["control"], "enabled_files": cohorts["enabled"],
    }
    manifest_path = root / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, sort_keys=True)); os.chmod(manifest_path, 0o600)
    report = {
        "archive_size_bytes": len(archive_bytes), "archive_sha256": digest(archive_bytes),
        "archive_member_count": 2016, "archive_readback_and_member_sha256_verification_passed": True,
        "run_exit_status": 0, "both_private_processes_returned_zero_status": True,
    }
    report_path = root / REPORT_NAME
    report_path.write_text(json.dumps(report, sort_keys=True)); os.chmod(report_path, 0o600)
    sums_path = root / SUMS_NAME
    sums_path.write_text(
        f"{digest(archive_bytes)}  {ARCHIVE_NAME}\n"
        f"{digest(manifest_path.read_bytes())}  {MANIFEST_NAME}\n"
        f"{digest(report_path.read_bytes())}  {REPORT_NAME}\n"
    )
    os.chmod(sums_path, 0o600)
    files = {
        "archive": archive, "manifest": manifest_path, "audit_report": report_path,
        "checksums": sums_path,
    }
    receipt = {
        "schema": "vh-saturn-stage143-drive-readback-receipt-1", "stage": 143,
        "owner_only": True, "readback_verified": True,
        "drive_file_id": "drive-file-archive", "manifest_drive_file_id": "drive-file-manifest",
        "audit_report_drive_file_id": "drive-file-report", "checksums_drive_file_id": "drive-file-sums",
    }
    for label, path in files.items():
        data = path.read_bytes()
        receipt[label + "_size_bytes"] = len(data)
        receipt[label + "_sha256"] = digest(data)
        receipt[label + "_readback_sha256"] = digest(data)
    receipt_path = root / RECEIPT_NAME
    receipt_path.write_text(json.dumps(receipt, sort_keys=True)); os.chmod(receipt_path, 0o600)
    files["receipt"] = receipt_path
    return files


class Stage143ArchiveGateTests(unittest.TestCase):
    def test_valid_owner_only_drive_readback_passes(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_fixture(Path(td))
            result = verify_private_stage143_archive(
                files["archive"], files["manifest"], files["audit_report"],
                files["checksums"], files["receipt"],
            )
            self.assertTrue(result["stage143_owner_only_drive_readback_verified"])
            self.assertEqual(result["archive_member_count"], 2016)
            self.assertTrue(result["all_member_hashes_match_manifest"])
            self.assertFalse(result["original_media_in_archive"])

    def test_local_only_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_fixture(Path(td))
            receipt = json.loads(files["receipt"].read_text())
            receipt["readback_verified"] = False
            files["receipt"].write_text(json.dumps(receipt)); os.chmod(files["receipt"], 0o600)
            with self.assertRaisesRegex(ValueError, "Drive readback receipt"):
                verify_private_stage143_archive(files["archive"], files["manifest"], files["audit_report"], files["checksums"], files["receipt"])

    def test_missing_drive_file_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_fixture(Path(td))
            receipt = json.loads(files["receipt"].read_text())
            receipt["manifest_drive_file_id"] = ""
            files["receipt"].write_text(json.dumps(receipt)); os.chmod(files["receipt"], 0o600)
            with self.assertRaisesRegex(ValueError, "Drive file ID"):
                verify_private_stage143_archive(files["archive"], files["manifest"], files["audit_report"], files["checksums"], files["receipt"])

    def test_archive_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_fixture(Path(td))
            with files["archive"].open("ab") as stream:
                stream.write(b"tamper")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                verify_private_stage143_archive(files["archive"], files["manifest"], files["audit_report"], files["checksums"], files["receipt"])

    def test_checksum_file_must_cover_exact_three_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_fixture(Path(td))
            files["checksums"].write_text("0" * 64 + "  fake.tar.gz\n"); os.chmod(files["checksums"], 0o600)
            with self.assertRaisesRegex(ValueError, "fingerprint mismatch|SHA256SUMS"):
                verify_private_stage143_archive(files["archive"], files["manifest"], files["audit_report"], files["checksums"], files["receipt"])


if __name__ == "__main__":
    unittest.main()
