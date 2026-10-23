"""Stage130 synthetic-only checks for safe private recapture handoff."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.saturn_private_stage130_storage_preflight import verify_new_capture_storage
from tools.saturn_private_stage130_recapture_handoff import recapture_with_durable_handoff


class Stage130PrivateHandoffTests(unittest.TestCase):
    def paths(self, root):
        a, b = root / "control", root / "enabled"
        a.mkdir(mode=0o700)
        b.mkdir(mode=0o700)
        return a, b, root / "new-archive.tar.gz", root / "readback.tar.gz"

    def test_private_preflight_accepts_distinct_empty_paths_only(self):
        with tempfile.TemporaryDirectory() as t:
            a, b, archive, readback = self.paths(Path(t))
            r = verify_new_capture_storage(a, b, archive, readback,
                                           "private:captures/new.tar.gz")
            self.assertTrue(r["new_capture_storage_preflight"])
            self.assertFalse(r["drive_upload_verified"])
            self.assertFalse(r["stage125_receipt_issued"])

    def test_preflight_rejects_nonempty_or_existing_outputs(self):
        with tempfile.TemporaryDirectory() as t:
            a, b, archive, readback = self.paths(Path(t))
            (a / "do-not-delete").write_text("SYNTHETIC")
            with self.assertRaisesRegex(ValueError, "empty"):
                verify_new_capture_storage(a, b, archive, readback, "private:c/new.tar.gz")
            self.assertTrue((a / "do-not-delete").exists())
            (a / "do-not-delete").unlink()
            readback.write_bytes(b"KEEP")
            with self.assertRaisesRegex(ValueError, "preexist"):
                verify_new_capture_storage(a, b, archive, readback, "private:c/new.tar.gz")
            self.assertEqual(readback.read_bytes(), b"KEEP")

    def test_preflight_rejects_unsafe_structure(self):
        with tempfile.TemporaryDirectory() as t:
            a, b, archive, readback = self.paths(Path(t))
            with self.assertRaises(ValueError):
                verify_new_capture_storage(a, a, archive, readback, "private:c/a")
            with self.assertRaises(ValueError):
                verify_new_capture_storage(a, b, archive, readback, "private:../escape")
            b.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "owner-only"):
                verify_new_capture_storage(a, b, archive, readback, "private:c/a")

    def test_rclone_must_exist_before_original_run(self):
        with tempfile.TemporaryDirectory() as t:
            a, b, archive, readback = self.paths(Path(t))
            with patch("tools.saturn_private_stage130_recapture_handoff.shutil.which",
                       return_value=None), patch(
                       "tools.saturn_private_stage130_recapture_handoff.run_private_prologue_continue_ninth_c"
                       ) as run:
                with self.assertRaisesRegex(ValueError, "rclone"):
                    self.run_pair(a, b, archive, readback)
                run.assert_not_called()

    def run_pair(self, a, b, archive, readback):
        return recapture_with_durable_handoff(
            a.parent / "missing.cue", a.parent / "missing1.bin", a.parent / "missing2.bin",
            a.parent / "runner", "a"*64, a, b, archive, "private:captures/new.tar.gz",
            readback)

    def test_complete_mocked_chain_never_claims_drive_acl(self):
        with tempfile.TemporaryDirectory() as t:
            a, b, archive, readback = self.paths(Path(t))
            with patch("tools.saturn_private_stage130_recapture_handoff.shutil.which",
                       return_value="/fake/rclone"), patch(
                       "tools.saturn_private_stage130_recapture_handoff.run_private_prologue_continue_ninth_c",
                       return_value={"checkpoint_png_count_per_process":900,
                                     "first_battle_or_player_control_verified":False}) as run, patch(
                       "tools.saturn_private_stage130_recapture_handoff.package_stage124_style_pair",
                       return_value={"stage124_paired_capture_audit_executed":True,
                                     "regular_members":1816,
                                     "historical_stage124_archive_recovered":False}) as pack, patch(
                       "tools.saturn_private_stage130_recapture_handoff._private_fingerprint",
                       return_value=(123, "a"*64, (1,2))) as fp, patch(
                       "tools.saturn_private_stage130_recapture_handoff.private_archive_roundtrip",
                       return_value={"configured_remote_roundtrip_verified":True,
                                     "stage125_drive_receipt_issued":False,
                                     "google_drive_owner_only_verified":False}) as transfer, patch(
                       "tools.saturn_private_stage130_recapture_handoff.audit_archived_stage124_pair",
                       return_value={"stage124_paired_capture_semantics_verified_in_archive":True}) as semantic:
                r = self.run_pair(a, b, archive, readback)
                self.assertTrue(r["fresh_recapture_handoff_passed"])
                self.assertFalse(r["owner_only_drive_acl_verified"])
                self.assertFalse(r["stage125_receipt_issued"])
                self.assertFalse(r["historical_stage124_archive_recovered"])
                run.assert_called_once()
                pack.assert_called_once()
                transfer.assert_called_once()
                semantic.assert_called_once()
                self.assertEqual(fp.call_count, 2)

    def test_failure_to_readback_never_calls_semantic_gate(self):
        with tempfile.TemporaryDirectory() as t:
            a, b, archive, readback = self.paths(Path(t))
            with patch("tools.saturn_private_stage130_recapture_handoff.shutil.which",
                       return_value="/fake/rclone"), patch(
                       "tools.saturn_private_stage130_recapture_handoff.run_private_prologue_continue_ninth_c",
                       return_value={"checkpoint_png_count_per_process":900,
                                     "first_battle_or_player_control_verified":False}), patch(
                       "tools.saturn_private_stage130_recapture_handoff.package_stage124_style_pair",
                       return_value={"stage124_paired_capture_audit_executed":True,
                                     "regular_members":1816,
                                     "historical_stage124_archive_recovered":False}), patch(
                       "tools.saturn_private_stage130_recapture_handoff._private_fingerprint",
                       return_value=(123,"a"*64,(1,2))), patch(
                       "tools.saturn_private_stage130_recapture_handoff.private_archive_roundtrip",
                       side_effect=ValueError("readback checksum mismatch")), patch(
                       "tools.saturn_private_stage130_recapture_handoff.audit_archived_stage124_pair"
                       ) as semantic:
                with self.assertRaisesRegex(ValueError, "checksum"):
                    self.run_pair(a, b, archive, readback)
                semantic.assert_not_called()


if __name__ == "__main__":
    unittest.main()
