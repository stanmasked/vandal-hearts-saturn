"""The repeat audit must fail closed on missing, corrupt or unsuccessful trials."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.nexium_repeat_audit import audit_trial, summarize


def fake(name, passed=True, selected=1):
    return {"trial": name, "passed": passed,
            "selected_input_attempt": selected}


class RepeatAuditTests(unittest.TestCase):
    def test_all_three_successes(self):
        with tempfile.TemporaryDirectory() as directory:
            r = summarize(Path(directory), lambda p: fake(p.name))
        self.assertTrue(r["all_independent_trials_passed"])
        self.assertEqual(r["passed_trials"], 3)
        self.assertEqual(r["first_attempt_successes"], 3)
        self.assertEqual(r["sample_size"], 3)

    def test_single_bad_trial_not_masked(self):
        with tempfile.TemporaryDirectory() as directory:
            r = summarize(Path(directory),
                          lambda p: fake(p.name, p.name != "trial-02"))
        self.assertFalse(r["all_independent_trials_passed"])
        self.assertEqual(r["failed_trials"], 1)
        self.assertEqual(r["passed_trials"], 2)

    def test_retry_accounted_without_overclaiming(self):
        with tempfile.TemporaryDirectory() as directory:
            r = summarize(Path(directory),
                          lambda p: fake(p.name, True, 2 if p.name == "trial-03" else 1))
        self.assertEqual(r["verified_retry_recoveries"], 1)
        self.assertEqual(r["first_attempt_successes"], 2)

    def test_missing_evidence_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            r = audit_trial(Path(directory) / "trial-01")
        self.assertFalse(r["passed"])
        self.assertEqual(r["error_type"], "FileNotFoundError")

    def test_bad_exit_receipt_fails_before_images(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "launcher-exit.txt").write_text("0; true\n")
            r = audit_trial(folder)
        self.assertFalse(r["passed"])
        self.assertEqual(r["error_type"], "ValueError")

    def test_nonzero_exit_never_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "launcher-exit.txt").write_text("124\n")
            with patch("tools.nexium_repeat_audit.Image.open",
                       side_effect=FileNotFoundError("missing frame")):
                r = audit_trial(folder)
        self.assertEqual(r["launcher_exit_code"], 124)
        self.assertFalse(r["passed"])

    def test_distinct_trial_names(self):
        with tempfile.TemporaryDirectory() as directory:
            called = []
            def audit(path):
                called.append(path.name)
                return fake(path.name)
            summarize(Path(directory), audit)
        self.assertEqual(called, ["trial-01", "trial-02", "trial-03"])


if __name__ == "__main__":
    unittest.main()
