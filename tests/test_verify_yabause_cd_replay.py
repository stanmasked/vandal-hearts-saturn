"""Stage85 audit rejects false receipts, modified sectors and leaked files."""
import tempfile
from pathlib import Path
import unittest

from tools.verify_yabause_cd_replay import (
    EXPECTED_SOURCE, EXPECTED_TRACE, GATE_NAME, LOG_NAME, SOURCE_NAME,
    SUCCESS, sha256, verify_trial, audit_repeated_runs,
)


class Stage85ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / SOURCE_NAME).write_bytes(EXPECTED_SOURCE)
        (self.root / LOG_NAME).write_bytes(EXPECTED_TRACE)

    def test_baseline_expected_synthetic_receipt(self):
        audit = verify_trial(self.root, SUCCESS + "\n")
        self.assertEqual(audit["source_bytes"], 4096)
        self.assertEqual(audit["trace_bytes"], len(EXPECTED_TRACE))
        self.assertEqual(audit["source_sha256"], sha256(EXPECTED_SOURCE))

    def test_rejects_extra_or_missing_success_receipt(self):
        for output in ("", SUCCESS + "\n" + SUCCESS + "\n", "not " + SUCCESS):
            with self.subTest(output=output), self.assertRaises(ValueError):
                verify_trial(self.root, output)

    def test_rejects_mutated_sector_payload(self):
        content = bytearray(EXPECTED_SOURCE)
        content[2020] ^= 0x01
        (self.root / SOURCE_NAME).write_bytes(content)
        with self.assertRaises(ValueError):
            verify_trial(self.root, SUCCESS + "\n")

    def test_rejects_extra_fad(self):
        (self.root / LOG_NAME).write_bytes(EXPECTED_TRACE + b"VHCD_FAD 152\n")
        with self.assertRaises(ValueError):
            verify_trial(self.root, SUCCESS + "\n")

    def test_rejects_malformed_fad_and_payload_leak(self):
        for val in (b"VHCD_FAD 151\nVHCD_FAD 150\n",
                    b"VHCD_FAD 150\r\nVHCD_FAD 151\n",
                    b"VHCD_DATA 0000\n" + EXPECTED_TRACE):
            (self.root / LOG_NAME).write_bytes(val)
            with self.subTest(val=val), self.assertRaises(ValueError):
                verify_trial(self.root, SUCCESS + "\n")

    def test_rejects_gate_left_behind(self):
        (self.root / GATE_NAME).write_text("1\n")
        with self.assertRaises(ValueError):
            verify_trial(self.root, SUCCESS + "\n")

    def test_rejects_other_files(self):
        (self.root / "unapproved-sector.bin").write_bytes(b"unexpected")
        with self.assertRaises(ValueError):
            verify_trial(self.root, SUCCESS + "\n")

    def test_rejects_symlinked_trace(self):
        log = self.root / LOG_NAME
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "outside.txt"
            target.write_bytes(EXPECTED_TRACE)
            log.unlink()
            log.symlink_to(target)
            # Only the two nominal names exist *inside* the workspace;
            # the rejection must therefore be specifically due to the symlink.
            self.assertEqual({x.name for x in self.root.iterdir()}, {SOURCE_NAME, LOG_NAME})
            with self.assertRaises(ValueError):
                verify_trial(self.root, SUCCESS + "\n")

    def test_rejects_workspace_not_empty(self):
        import sys
        # Use a genuine executable so the negative outcome is caused by
        # dirty workspace state, not an unrelated non-executable fixture.
        with self.assertRaises(ValueError):
            audit_repeated_runs(Path(sys.executable), self.root)


if __name__ == "__main__":
    unittest.main()
