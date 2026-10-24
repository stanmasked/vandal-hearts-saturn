"""Synthetic-only tests for the Stage145 private archive readback gate."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

from tools.saturn_private_stage145_archive_gate import (
    ARCHIVE_NAME, BUNDLE_NAME, CHECKSUMS_NAME, MANIFEST_NAME, REPORT_NAME,
    verify_private_stage145_archive,
)

SIDECARS = {
    "fad.vhcdlog", "frames.stats", "pad-events.txt", "pad-state.txt",
    "post.png", "pre.png", "sh2-window.txt", "video-state.txt",
}
FRAME_NAMES = {f"frame-{n}.png" for n in range(120, 144001, 120)}
EXPECTED = {f"{cohort}/{name}" for cohort in ("control", "enabled") for name in (FRAME_NAMES | SIDECARS)}
FOLDER = "private-stage145-folder"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_private(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    path.chmod(0o600)


def write_tar(path: Path, members: dict[str, bytes]) -> None:
    with path.open("xb") as raw:
        os.chmod(path, 0o600)
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                for name, data in sorted(members.items()):
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mode = 0o600
                    info.mtime = 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    tar.addfile(info, io.BytesIO(data))
        raw.flush()
        os.fsync(raw.fileno())


def build_fixture(root: Path) -> dict[str, Path]:
    payloads = {name: (b"x" if name.endswith(".png") else b"s") for name in EXPECTED}
    archive = root / ARCHIVE_NAME
    write_tar(archive, payloads)
    archive_bytes = archive.read_bytes()
    archive_hash = digest(archive_bytes)
    members = [{"path": name, "size_bytes": len(data), "sha256": digest(data)} for name, data in sorted(payloads.items())]
    manifest = {
        "schema": "vh-saturn-stage145-raw-capture-manifest-1",
        "stage": 145,
        "experiment": "source-patched-release-full-144000-frame-twelfth-C-paired-run",
        "archive_file_name": ARCHIVE_NAME,
        "archive_size_bytes": len(archive_bytes),
        "archive_sha256": archive_hash,
        "contains_original_disc_media": False,
        "contains_derived_audit_report": False,
        "contains_runner_binary": False,
        "cohorts": {"control": 1200, "enabled": 1200},
        "raw_member_count": 2416,
        "raw_payload_bytes": sum(map(len, payloads.values())),
        "members": members,
    }
    manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    manifest_path = root / MANIFEST_NAME
    write_private(manifest_path, manifest_bytes)
    nested = {
        "kind": "STAGE145_PRIVATE_PROLOGUE_CONTINUE_TWELFTH_C_INTEGRITY_ONLY",
        "all_checkpoint_pngs_and_diagnostic_sequences_verified": True,
        "checkpoint_png_count_per_process": 1200,
        "same_dimensions_across_runs": True,
        "shared_tenth_C_press_frame": 108000,
        "shared_tenth_C_release_frame": 108006,
        "shared_eleventh_C_press_frame": 120000,
        "shared_eleventh_C_release_frame": 120006,
        "twelfth_C_press_frame": 132000,
        "twelfth_C_release_frame": 132006,
        "twelfth_press_checkpoint_equal": True,
        "pre_twelfth_checkpoint_equal_count": 1099,
        "pre_twelfth_checkpoint_total": 1099,
        "first_post_twelfth_framebuffer_divergence_by_133200": 132120,
        "first_post_twelfth_framebuffer_divergence_through_144000": 132120,
        "frame_144000_differs": True,
        "control_cd_event_count": 58538,
        "intervention_cd_event_count": 58538,
        "cd_logs_differ": False,
        "first_battle_or_player_control_verified": False,
        "original_media_or_frame_hashes_exported": False,
    }
    report = {
        "schema": "vh-saturn-stage145-full-pair-audit-1",
        "kind": "STAGE145_FULL_PRIVATE_PAIR_AUDIT",
        "stage": 145,
        "paired_cold_boot_processes": 2,
        "frames_per_process": 144000,
        "checkpoint_png_count_per_process": 1200,
        "all_pngs_decoded_and_crc_validated": True,
        "all_pad_receipts_and_diagnostic_sequences_verified": True,
        "source_media_and_runner_unchanged_before_after": True,
        "stage144_drive_readback_receipt_verified": True,
        "stage144_owner_only_drive_readback_gate": {"stage144_owner_only_drive_readback_verified": True},
        "twelfth_c_effect_on_original_framebuffer_confirmed": True,
        "first_post_twelfth_framebuffer_divergence": 132120,
        "pre_twelfth_checkpoint_pairs_identical": 1099,
        "frame_144000_differs": True,
        "first_battle_or_player_control_verified": False,
        "original_media_or_frame_hashes_exported": False,
        "paired_capture_audit": nested,
    }
    report_bytes = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
    report_path = root / REPORT_NAME
    write_private(report_path, report_bytes)
    checksum_bytes = (
        f"{archive_hash}  {ARCHIVE_NAME}\n"
        f"{digest(manifest_bytes)}  {MANIFEST_NAME}\n"
        f"{digest(report_bytes)}  {REPORT_NAME}\n"
    ).encode("ascii")
    checksums_path = root / CHECKSUMS_NAME
    write_private(checksums_path, checksum_bytes)
    bundle_entries = {
        "manifest/" + MANIFEST_NAME: manifest_bytes,
        "reports/" + REPORT_NAME: report_bytes,
        "checksums/" + ARCHIVE_NAME + ".sha256": f"{archive_hash}  {ARCHIVE_NAME}\n".encode(),
        "checksums/" + MANIFEST_NAME + ".sha256": f"{digest(manifest_bytes)}  {MANIFEST_NAME}\n".encode(),
        "checksums/" + REPORT_NAME + ".sha256": f"{digest(report_bytes)}  {REPORT_NAME}\n".encode(),
        "README.txt": (
            "Vandal Hearts Saturn Stage145 metadata bundle\n"
            "The raw capture archive is a separate owner-only Drive file.\n"
            "Drive file ID: archive-drive-id\n"
            f"Archive size: {len(archive_bytes)}\n"
            f"Archive SHA-256: {archive_hash}\n"
            "An independent Drive download/readback matched that size and SHA-256.\n"
        ).encode(),
    }
    bundle_path = root / BUNDLE_NAME
    write_tar(bundle_path, bundle_entries)
    receipt = {
        "schema": "vh-saturn-stage145-drive-readback-receipt-1",
        "stage": 145,
        "owner_only": True,
        "readback_verified": True,
        "archive_shared": False,
        "metadata_bundle_shared": False,
        "manifest_shared": False,
        "audit_report_shared": False,
        "checksums_shared": False,
        "drive_file_id": "archive-drive-id",
        "metadata_bundle_drive_file_id": "bundle-drive-id",
        "manifest_drive_file_id": "manifest-drive-id",
        "audit_report_drive_file_id": "report-drive-id",
        "checksums_drive_file_id": "checksums-drive-id",
        "private_folder_id": FOLDER,
        "archive_parent_folder_id": FOLDER,
        "metadata_bundle_parent_folder_id": FOLDER,
        "manifest_parent_folder_id": FOLDER,
        "audit_report_parent_folder_id": FOLDER,
        "checksums_parent_folder_id": FOLDER,
    }
    files = {"archive": archive, "manifest": manifest_path, "audit_report": report_path,
             "checksums": checksums_path, "metadata_bundle": bundle_path}
    for label, path in files.items():
        data = path.read_bytes()
        receipt[label + "_size_bytes"] = len(data)
        receipt[label + "_sha256"] = digest(data)
        receipt[label + "_readback_sha256"] = digest(data)
    receipt_path = root / "stage145-drive-readback-receipt.json"
    write_private(receipt_path, json.dumps(receipt, sort_keys=True).encode())
    files["receipt"] = receipt_path
    return files


class Stage145ArchiveReadbackGateTests(unittest.TestCase):
    def verify(self, files):
        return verify_private_stage145_archive(
            files["archive"], files["manifest"], files["audit_report"],
            files["checksums"], files["metadata_bundle"], files["receipt"],
        )

    def test_complete_owner_only_readback_gate_passes(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.verify(build_fixture(Path(td)))
            self.assertTrue(result["stage145_owner_only_drive_readback_verified"])
            self.assertEqual(result["archive_member_count"], 2416)
            self.assertEqual(result["frames_per_cohort"], 1200)
            self.assertTrue(result["all_member_hashes_match_manifest"])
            self.assertFalse(result["original_media_in_archive"])
            self.assertFalse(result["runner_binary_in_archive"])

    def test_archive_mutation_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_fixture(Path(td))
            with files["archive"].open("ab") as stream:
                stream.write(b"tamper")
            with self.assertRaisesRegex(ValueError, "archive fingerprint"):
                self.verify(files)

    def test_shared_bundle_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_fixture(Path(td))
            receipt = json.loads(files["receipt"].read_text())
            receipt["metadata_bundle_shared"] = True
            write_private(files["receipt"], json.dumps(receipt).encode())
            with self.assertRaisesRegex(ValueError, "owner-only Drive readback receipt"):
                self.verify(files)

    def test_report_cannot_claim_player_control(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_fixture(Path(td))
            report = json.loads(files["audit_report"].read_text())
            report["first_battle_or_player_control_verified"] = True
            write_private(files["audit_report"], json.dumps(report).encode())
            with self.assertRaisesRegex(ValueError, "aggregate audit report"):
                self.verify(files)

    def test_report_must_confirm_press_checkpoint_equal(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_fixture(Path(td))
            report = json.loads(files["audit_report"].read_text())
            report["paired_capture_audit"]["twelfth_press_checkpoint_equal"] = False
            write_private(files["audit_report"], json.dumps(report).encode())
            with self.assertRaisesRegex(ValueError, "aggregate audit report"):
                self.verify(files)

    def test_archive_readback_hash_must_match_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            files = build_fixture(Path(td))
            receipt = json.loads(files["receipt"].read_text())
            receipt["archive_readback_sha256"] = "0" * 64
            write_private(files["receipt"], json.dumps(receipt).encode())
            with self.assertRaisesRegex(ValueError, "Drive readback archive SHA-256 mismatch"):
                self.verify(files)


if __name__ == "__main__":
    unittest.main()
