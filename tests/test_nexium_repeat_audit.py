"""The repeat audit must fail closed on missing, corrupt or unsuccessful trials."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.nexium_repeat_audit import audit_trial, summarize, parse_attempt_receipt


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

    def test_sixth_pulse_counts_as_verified_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            report = summarize(
                Path(directory),
                lambda path: fake(path.name, True, 6 if path.name == "trial-02" else 1))
        self.assertTrue(report["all_independent_trials_passed"])
        self.assertEqual(report["verified_retry_recoveries"], 1)
        self.assertEqual(report["first_attempt_successes"], 2)

    def test_sixth_observed_pulse_can_win_after_five_misses(self):
        # Exact failure shape observed in NeXium Stage44 and Stage45.
        attempts = "probe=bounded_right_v2\nmax_attempts=8\n"
        for n in range(1, 6):
            attempts += f"attempt{n}=no_verified_movement\n"
            attempts += f"focus_after_attempt_{n}=sent\n"
        attempts += "attempt6=visible_movement\nselected_attempt=6\n"
        self.assertEqual(parse_attempt_receipt(attempts), (6, 8, True))

    def test_selected_none_always_fails(self):
        attempts = "probe=bounded_right_v2\nmax_attempts=8\n"
        attempts += "".join(f"attempt{n}=no_verified_movement\n"
                            for n in range(1, 9))
        attempts += "selected_attempt=none\n"
        with self.assertRaisesRegex(ValueError, "unverified"):
            parse_attempt_receipt(attempts)

    def test_out_of_range_attempt_not_accepted(self):
        with self.assertRaisesRegex(ValueError, "bounded"):
            parse_attempt_receipt(
                "probe=bounded_right_v2\nmax_attempts=8\n"
                "attempt9=visible_movement\nselected_attempt=9\n")

    def test_winner_must_have_visible_motion_receipt(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            parse_attempt_receipt(
                "probe=bounded_right_v2\nmax_attempts=8\n"
                "attempt4=no_verified_movement\nselected_attempt=4\n")

    def test_duplicate_or_forged_selection_receipt_fails(self):
        with self.assertRaises(ValueError):
            parse_attempt_receipt(
                "probe=bounded_right_v2\nmax_attempts=8\n"
                "attempt3=visible_movement\nselected_attempt=3\n"
                "selected_attempt=3\n")
        with self.assertRaises(ValueError):
            parse_attempt_receipt(
                "probe=bounded_right_v2\nmax_attempts=8\n"
                "attempt3=visible_movement\nattempt4=visible_movement\n"
                "selected_attempt=4\n")

    def test_legacy_two_attempt_receipt_still_recognized(self):
        old = ("probe=bounded_right_v1\n"
               "attempt1=no_verified_movement\n"
               "attempt2=visible_movement\nselected_attempt=2\n")
        self.assertEqual(parse_attempt_receipt(old), (2, 2, False))

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
