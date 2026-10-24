"""Stage132 invented-only remote connectivity probe tests; no Drive credentials."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.saturn_private_stage132_remote_canary import verify_private_remote_canary
from tools.saturn_private_stage130_recapture_handoff import recapture_with_durable_handoff

TARGET = "owner:VH-Saturn/Private Archives/Stage124/new.tar.gz"


class Stage132RemoteCanaryTests(unittest.TestCase):
    def test_synthetic_write_read_cleanup(self):
        seen = []
        stored = {}
        def fake_command(_exe, args):
            seen.append(args[0])
            if args[0] == "copyto" and args[1].endswith("/canary"):
                self.assertIn("--immutable", args)
                stored["bytes"] = Path(args[1]).read_bytes()
                stored["path"] = args[2]
            elif args[0] == "copyto":
                self.assertEqual(args[1], stored["path"])
                Path(args[2]).write_bytes(stored["bytes"])
            elif args[0] == "deletefile":
                self.assertEqual(args[1], stored["path"])
            else:
                self.fail("unexpected command")
        with patch("tools.saturn_private_stage132_remote_canary.shutil.which",
                   return_value="/private/rclone"), patch(
            "tools.saturn_private_stage132_remote_canary._command",
            side_effect=fake_command
        ):
            report = verify_private_remote_canary(TARGET)
        self.assertEqual(seen, ["copyto", "copyto", "deletefile"])
        self.assertTrue(report["synthetic_private_remote_write_read_delete_verified"])
        self.assertFalse(report["owner_only_google_drive_permissions_verified"])
        self.assertFalse(report["original_archive_uploaded"])
        self.assertFalse(report["stage125_receipt_issued"])

    def test_corrupt_readback_fails_and_deletes_only_canary(self):
        seen = []
        def corrupt(_exe, args):
            seen.append(args[0])
            if args[0] == "copyto" and args[1].endswith(".txt"):
                Path(args[2]).write_bytes(b"INVENTED-WRONG-CANARY")
        with patch("tools.saturn_private_stage132_remote_canary.shutil.which",
                   return_value="/private/rclone"), patch(
            "tools.saturn_private_stage132_remote_canary._command",
            side_effect=corrupt
        ):
            with self.assertRaisesRegex(ValueError, "canary not verified"):
                verify_private_remote_canary(TARGET)
        self.assertEqual(seen, ["copyto", "copyto", "deletefile"])

    def test_cleanup_failure_is_fatal(self):
        def fail_cleanup(_exe, args):
            if args[0] == "deletefile":
                raise ValueError("synthetic delete not confirmed")
            if args[0] == "copyto" and args[1].endswith(".txt"):
                # Write original probe bytes based on previous source.
                Path(args[2]).write_bytes(self.canary)
            elif args[0] == "copyto":
                self.canary = Path(args[1]).read_bytes()
        with patch("tools.saturn_private_stage132_remote_canary.shutil.which",
                   return_value="/private/rclone"), patch(
            "tools.saturn_private_stage132_remote_canary._command",
            side_effect=fail_cleanup
        ):
            with self.assertRaisesRegex(ValueError, "cleanup not verified"):
                verify_private_remote_canary(TARGET)

    def test_unconfigured_remote_rejected_before_transfer(self):
        for bad in ("owner:../escape.tar.gz", "owner:/abs/out.tar.gz",
                    "owner:singlefile.tar.gz"):
            with self.subTest(target=bad):
                with patch("tools.saturn_private_stage132_remote_canary._command") as cmd:
                    with self.assertRaises(ValueError):
                        verify_private_remote_canary(bad)
                    cmd.assert_not_called()

    def test_stage124_runner_blocked_when_probe_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            control, enabled = base/"control", base/"enabled"
            control.mkdir(mode=0o700)
            enabled.mkdir(mode=0o700)
            with patch(
                "tools.saturn_private_stage130_recapture_handoff.shutil.which",
                return_value="/private/rclone"
            ), patch(
                "tools.saturn_private_stage130_recapture_handoff.verify_private_remote_canary",
                side_effect=ValueError("SYNTHETIC-REMOTE-DOWN")
            ) as probe, patch(
                "tools.saturn_private_stage130_recapture_handoff.run_private_prologue_continue_ninth_c"
            ) as original_run:
                with self.assertRaisesRegex(ValueError, "SYNTHETIC-REMOTE-DOWN"):
                    recapture_with_durable_handoff(
                        base/"source.cue",base/"track1.bin",base/"track2.bin",
                        base/"runner","a"*64,control,enabled,
                        base/"fresh.tar.gz",TARGET,base/"readback.tar.gz")
                probe.assert_called_once()
                original_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
