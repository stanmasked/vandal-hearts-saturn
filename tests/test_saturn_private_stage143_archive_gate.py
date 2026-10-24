"""Synthetic-only Stage143 archive gate tests; no game media is used."""
import gzip
import io
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


RAW_ARCHIVE_NAME = "stage143-full120000-raw-captures.tar.gz"
RAW_MANIFEST_NAME = "stage143-full120000-raw-manifest.json"
RAW_REPORT_NAME = "stage143-full-pair-audit.json"
RAW_BUNDLE_NAME = "stage143-full120000-metadata-bundle.tar.gz"
RAW_RECEIPT_NAME = "stage143-drive-readback-receipt.json"
RAW_SIDECARS = {
    "fad.vhcdlog", "frames.stats", "pad-events.txt", "pad-state.txt",
    "post.png", "pre.png", "sh2-window.txt", "video-state.txt",
}


def build_raw_bundle_fixture(root: Path):
    frame_names = {f"frame-{n}.png" for n in range(120, 120001, 120)}
    expected = {f"{cohort}/{name}" for cohort in ("control", "enabled")
                for name in (frame_names | RAW_SIDECARS)}
    payloads = {name: (b"x" if name.endswith(".png") else b"s") for name in expected}
    archive = root / RAW_ARCHIVE_NAME
    with archive.open("xb") as raw_file:
        os.chmod(archive, 0o600)
        with gzip.GzipFile(filename="", fileobj=raw_file, mode="wb", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                for name, data in sorted(payloads.items()):
                    info = tarfile.TarInfo(name)
                    info.size = len(data); info.mode = 0o600; info.mtime = 0
                    info.uid = info.gid = 0; info.uname = info.gname = ""
                    tar.addfile(info, io.BytesIO(data))
        raw_file.flush(); os.fsync(raw_file.fileno())
    archive_bytes = archive.read_bytes()
    archive_hash = digest(archive_bytes)
    members = [
        {"path": name, "size_bytes": len(data), "sha256": digest(data)}
        for name, data in sorted(payloads.items())
    ]
    manifest = {
        "schema": "vh-saturn-stage143-raw-capture-manifest-1",
        "stage": 143,
        "experiment": "source-patched-release-full-120000-paired-run",
        "archive_file_name": RAW_ARCHIVE_NAME,
        "archive_size_bytes": len(archive_bytes),
        "archive_sha256": archive_hash,
        "contains_original_disc_media": False,
        "contains_derived_audit_report": False,
        "cohorts": {"control": 1000, "enabled": 1000},
        "raw_member_count": 2016,
        "raw_payload_bytes": sum(len(v) for v in payloads.values()),
        "members": members,
    }
    manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    manifest_path = root / RAW_MANIFEST_NAME
    manifest_path.write_bytes(manifest_bytes); os.chmod(manifest_path, 0o600)
    report = {
        "schema": "vh-saturn-stage143-full-pair-audit-1",
        "kind": "STAGE143_FULL_PRIVATE_PAIR_AUDIT",
        "stage": 143,
        "paired_cold_boot_processes": 2,
        "frames_per_process": 120000,
        "checkpoint_png_count_per_process": 1000,
        "all_pngs_decoded_and_crc_validated": True,
        "all_pad_receipts_and_diagnostic_sequences_verified": True,
        "source_media_and_runner_unchanged_per_controller_receipt": True,
        "tenth_c_effect_on_original_framebuffer_confirmed": True,
        "first_post_tenth_framebuffer_divergence": 108120,
        "pre_tenth_checkpoint_pairs_identical": 899,
        "post_tenth_checkpoint_pairs_different": 100,
        "first_battle_or_player_control_verified": False,
        "original_media_or_frame_hashes_exported": False,
    }
    report_bytes = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
    report_path = root / RAW_REPORT_NAME
    report_path.write_bytes(report_bytes); os.chmod(report_path, 0o600)

    bundle_entries = {
        "manifest/" + RAW_MANIFEST_NAME: manifest_bytes,
        "reports/" + RAW_REPORT_NAME: report_bytes,
        "checksums/" + RAW_ARCHIVE_NAME + ".sha256":
            f"{archive_hash}  {RAW_ARCHIVE_NAME}\n".encode(),
        "checksums/" + RAW_MANIFEST_NAME + ".sha256":
            f"{digest(manifest_bytes)}  {RAW_MANIFEST_NAME}\n".encode(),
        "checksums/" + RAW_REPORT_NAME + ".sha256":
            f"{digest(report_bytes)}  /mnt/data/{RAW_REPORT_NAME}\n".encode(),
        "README.txt": (
            "Vandal Hearts Saturn Stage143 metadata bundle\n"
            "The raw capture archive is a separate owner-only Drive file.\n"
            "Drive file ID: drive-file-archive\n"
            f"Archive size: {len(archive_bytes)}\n"
            f"Archive SHA-256: {archive_hash}\n"
            "An independent Drive download/readback matched that size and SHA-256; "
            "the tar listing contains 2016 files.\n"
        ).encode(),
    }
    bundle_path = root / RAW_BUNDLE_NAME
    with bundle_path.open("xb") as raw_file:
        os.chmod(bundle_path, 0o600)
        with gzip.GzipFile(filename="", fileobj=raw_file, mode="wb", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                for name, data in sorted(bundle_entries.items()):
                    info = tarfile.TarInfo(name)
                    info.size = len(data); info.mode = 0o600; info.mtime = 0
                    info.uid = info.gid = 0; info.uname = info.gname = ""
                    tar.addfile(info, io.BytesIO(data))
        raw_file.flush(); os.fsync(raw_file.fileno())
    bundle_hash = digest(bundle_path.read_bytes())
    receipt = {
        "schema": "vh-saturn-stage143-drive-readback-receipt-2",
        "stage": 143,
        "owner_only": True,
        "readback_verified": True,
        "archive_shared": False,
        "metadata_bundle_shared": False,
        "drive_file_id": "drive-file-archive",
        "metadata_bundle_drive_file_id": "drive-file-bundle",
        "private_folder_id": "private-folder",
        "archive_parent_folder_id": "private-folder",
        "metadata_bundle_parent_folder_id": "private-folder",
    }
    for label, path in (
        ("archive", archive), ("manifest", manifest_path),
        ("audit_report", report_path), ("metadata_bundle", bundle_path),
    ):
        data = path.read_bytes()
        receipt[label + "_size_bytes"] = len(data)
        receipt[label + "_sha256"] = digest(data)
        receipt[label + "_readback_sha256"] = digest(data)
    receipt_path = root / RAW_RECEIPT_NAME
    receipt_path.write_text(json.dumps(receipt, sort_keys=True)); os.chmod(receipt_path, 0o600)
    return {
        "archive": archive, "manifest": manifest_path, "audit_report": report_path,
        "metadata_bundle": bundle_path, "receipt": receipt_path,
        "manifest_bytes": manifest_bytes, "report_bytes": report_bytes,
        "bundle_hash": bundle_hash,
    }


class Stage143RawDriveReadbackGateTests(unittest.TestCase):
    def verify(self, files):
        return verify_private_stage143_archive(
            files["archive"], files["manifest"], files["audit_report"],
            files["metadata_bundle"], files["receipt"],
        )

    def test_actual_raw_manifest_and_metadata_bundle_contract_passes(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_raw_bundle_fixture(Path(td))
            result = self.verify(files)
            self.assertTrue(result["stage143_owner_only_drive_readback_verified"])
            self.assertEqual(result["schema"], "vh-saturn-stage143-drive-readback-gate-2")
            self.assertEqual(result["archive_member_count"], 2016)
            self.assertEqual(result["raw_payload_bytes"], 2016)
            self.assertTrue(result["all_member_hashes_match_manifest"])
            self.assertFalse(result["original_media_in_archive"])
            self.assertEqual(result["metadata_bundle_sha256"], files["bundle_hash"])

    def test_raw_archive_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_raw_bundle_fixture(Path(td))
            with files["archive"].open("ab") as stream:
                stream.write(b"tamper")
            with self.assertRaisesRegex(ValueError, "archive fingerprint"):
                self.verify(files)

    def test_readback_receipt_must_attest_owner_only_files(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_raw_bundle_fixture(Path(td))
            receipt = json.loads(files["receipt"].read_text())
            receipt["metadata_bundle_shared"] = True
            files["receipt"].write_text(json.dumps(receipt)); os.chmod(files["receipt"], 0o600)
            with self.assertRaisesRegex(ValueError, "owner-only Drive readback receipt"):
                self.verify(files)

    def test_metadata_bundle_must_match_separately_extracted_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_raw_bundle_fixture(Path(td))
            changed = files["manifest"].read_bytes() + b"\n"
            files["manifest"].write_bytes(changed); os.chmod(files["manifest"], 0o600)
            receipt = json.loads(files["receipt"].read_text())
            receipt["manifest_size_bytes"] = len(changed)
            receipt["manifest_sha256"] = digest(changed)
            receipt["manifest_readback_sha256"] = digest(changed)
            files["receipt"].write_text(json.dumps(receipt)); os.chmod(files["receipt"], 0o600)
            with self.assertRaisesRegex(ValueError, "metadata bundle differs"):
                self.verify(files)

    def test_metadata_bundle_readback_hash_must_match_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_raw_bundle_fixture(Path(td))
            receipt = json.loads(files["receipt"].read_text())
            receipt["metadata_bundle_readback_sha256"] = "0" * 64
            files["receipt"].write_text(json.dumps(receipt)); os.chmod(files["receipt"], 0o600)
            with self.assertRaisesRegex(ValueError, "Drive readback metadata_bundle SHA-256 mismatch"):
                self.verify(files)

    def test_manifest_cannot_admit_original_media_member(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files = build_raw_bundle_fixture(root)
            manifest = json.loads(files["manifest"].read_text())
            manifest["members"][0]["path"] = "control/disc-track-1.bin"
            manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
            files["manifest"].write_bytes(manifest_bytes); os.chmod(files["manifest"], 0o600)

            # Keep the bundle internally consistent so the gate reaches its
            # canonical-path validation rather than failing an earlier hash check.
            with tarfile.open(files["metadata_bundle"], "r:gz") as tar:
                entries = {m.name: tar.extractfile(m).read() for m in tar.getmembers()}
            entries["manifest/" + RAW_MANIFEST_NAME] = manifest_bytes
            entries["checksums/" + RAW_MANIFEST_NAME + ".sha256"] = (
                f"{digest(manifest_bytes)}  {RAW_MANIFEST_NAME}\n".encode()
            )
            temp_bundle = root / "rebuilt-metadata-bundle.tar.gz"
            with temp_bundle.open("xb") as raw_file:
                os.chmod(temp_bundle, 0o600)
                with gzip.GzipFile(filename="", fileobj=raw_file, mode="wb", mtime=0) as gz:
                    with tarfile.open(fileobj=gz, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                        for name, data in sorted(entries.items()):
                            info = tarfile.TarInfo(name)
                            info.size = len(data); info.mode = 0o600; info.mtime = 0
                            info.uid = info.gid = 0; info.uname = info.gname = ""
                            tar.addfile(info, io.BytesIO(data))
                raw_file.flush(); os.fsync(raw_file.fileno())
            temp_bundle.replace(files["metadata_bundle"])
            os.chmod(files["metadata_bundle"], 0o600)

            receipt = json.loads(files["receipt"].read_text())
            receipt["manifest_size_bytes"] = len(manifest_bytes)
            receipt["manifest_sha256"] = digest(manifest_bytes)
            receipt["manifest_readback_sha256"] = digest(manifest_bytes)
            bundle_bytes = files["metadata_bundle"].read_bytes()
            receipt["metadata_bundle_size_bytes"] = len(bundle_bytes)
            receipt["metadata_bundle_sha256"] = digest(bundle_bytes)
            receipt["metadata_bundle_readback_sha256"] = digest(bundle_bytes)
            files["receipt"].write_text(json.dumps(receipt)); os.chmod(files["receipt"], 0o600)
            with self.assertRaisesRegex(ValueError, "raw manifest member path/size/hash invalid"):
                self.verify(files)


if __name__ == "__main__":
    unittest.main()
