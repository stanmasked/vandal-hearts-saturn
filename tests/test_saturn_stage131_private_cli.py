"""Stage131: safe CLI entrypoint to Stage130 private handoff, invented-only."""
import contextlib
import io
import json
from pathlib import Path
from unittest.mock import patch
import unittest

from tools.saturn_private_stage130_recapture_handoff import main


ARGS = ["--cue", "/private/in.cue", "--track1", "/private/t1.bin",
        "--track2", "/private/t2.bin", "--runner", "/private/emulator",
        "--runner-sha256", "0" * 64, "--control", "/private/control",
        "--enabled", "/private/enabled", "--archive", "/private/out.tar.gz",
        "--readback", "/private/download.tar.gz",
        "--remote-object", "owner:captured/new.tar.gz"]


class Stage131PrivateCliTests(unittest.TestCase):
    def test_cli_success_reports_only_bounded_nonprivate_status(self):
        status = {"stage": 130, "fresh_recapture_handoff_passed": True,
                  "stage125_receipt_issued": False,
                  "owner_only_drive_acl_verified": False}
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("sys.argv", ["private-handoff"] + ARGS), patch(
            "tools.saturn_private_stage130_recapture_handoff.recapture_with_durable_handoff",
            return_value=status,
        ) as work, contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(main(), 0)
        report = json.loads(stdout.getvalue())
        self.assertEqual(report, status)
        self.assertEqual(stderr.getvalue(), "")
        work.assert_called_once()
        self.assertIsInstance(work.call_args.args[0], Path)
        self.assertEqual(len(work.call_args.args), 10)

    def test_private_failure_reports_no_sensitive_paths(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("sys.argv", ["private-handoff"] + ARGS), patch(
            "tools.saturn_private_stage130_recapture_handoff.recapture_with_durable_handoff",
            side_effect=ValueError("private vault object owner:captured/new.tar.gz"),
        ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(main(), 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("STAGE130_PRIVATE_HANDOFF_REJECTED", stderr.getvalue())
        self.assertNotIn("owner:captured", stderr.getvalue())
        self.assertNotIn("/private", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
