"""Synthetic-only Stage145 package builder tests; no original disc or emulator."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.saturn_private_prologue_continue_twelfth_c_audit import audit_private_prologue_continue_twelfth_c
from tools.saturn_private_stage145_archive_gate import verify_private_stage145_archive
from tools.saturn_private_stage145_capture_packager import (
    ARCHIVE_NAME, BUNDLE_NAME, CHECKSUMS_NAME, MANIFEST_NAME, REPORT_NAME,
    build_metadata_bundle, build_raw_package, build_receipt,
)
from tests.test_saturn_private_prologue_continue_twelfth_c_audit import _make_pair


def _sha(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Stage145CapturePackagerTests(unittest.TestCase):
    def test_raw_bundle_receipt_and_gate_round_trip_with_synthetic_pair(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            capture_root = root / "captures"
            capture_root.mkdir(mode=0o700)
            control, enabled = _make_pair(capture_root)
            audit = audit_private_prologue_continue_twelfth_c(control, enabled)
            runner_report = {
                "schema": "vh-saturn-stage145-private-pair-run-1",
                "stage": 145,
                "run_exit_status": 0,
                "both_private_processes_returned_zero_status": True,
                "original_media_unchanged_before_after": True,
                "runner_unchanged_before_after": True,
                "runner_sha256_matches_pinned_release": True,
                "stage144_drive_readback_receipt_verified": True,
                "stage144_owner_only_drive_readback_gate": {
                    "stage144_owner_only_drive_readback_verified": True,
                },
                "paired_capture_audit": audit,
                "original_media_or_frame_hashes_exported": False,
                "full_playable_battle_or_unit_control_verified": False,
            }
            report_path = root / "runner-report.json"
            report_path.write_text(json.dumps(runner_report), encoding="utf-8")
            report_path.chmod(0o600)
            out = root / "package"
            out.mkdir(mode=0o700)

            result = build_raw_package(control, enabled, report_path, out)
            self.assertEqual(result["raw_member_count"], 2416)
            self.assertTrue(result["independent_pair_audit_passed"])
            archive = out / ARCHIVE_NAME
            manifest = out / MANIFEST_NAME
            report = out / REPORT_NAME
            checksums = out / CHECKSUMS_NAME
            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            report_data = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(manifest_data["raw_member_count"], 2416)
            self.assertEqual(report_data["first_post_twelfth_framebuffer_divergence"], 132120)
            self.assertFalse(report_data["first_battle_or_player_control_verified"])

            bundle_result = build_metadata_bundle(
                out, archive_drive_file_id="synthetic-archive-id",
                archive_readback_size_bytes=archive.stat().st_size,
                archive_readback_sha256=_sha(archive),
            )
            bundle = out / BUNDLE_NAME
            self.assertEqual(bundle_result["sha256"], _sha(bundle))

            ids = {
                "drive_file_id": "synthetic-archive-id",
                "metadata_bundle_drive_file_id": "synthetic-bundle-id",
                "manifest_drive_file_id": "synthetic-manifest-id",
                "audit_report_drive_file_id": "synthetic-report-id",
                "checksums_drive_file_id": "synthetic-checksums-id",
                "private_folder_id": "synthetic-private-folder",
                "archive_parent_folder_id": "synthetic-private-folder",
                "metadata_bundle_parent_folder_id": "synthetic-private-folder",
                "manifest_parent_folder_id": "synthetic-private-folder",
                "audit_report_parent_folder_id": "synthetic-private-folder",
                "checksums_parent_folder_id": "synthetic-private-folder",
            }
            for label, path in (("archive", archive), ("metadata_bundle", bundle),
                                ("manifest", manifest), ("audit_report", report),
                                ("checksums", checksums)):
                ids[label + "_size_bytes"] = path.stat().st_size
                ids[label + "_sha256"] = _sha(path)
                ids[label + "_readback_sha256"] = _sha(path)
            receipt = build_receipt(out, ids)
            gate = verify_private_stage145_archive(archive, manifest, report, checksums, bundle, receipt)
            self.assertTrue(gate["stage145_owner_only_drive_readback_verified"])
            self.assertEqual(gate["archive_member_count"], 2416)
            self.assertTrue(gate["all_member_hashes_match_manifest"])


if __name__ == "__main__":
    unittest.main()
