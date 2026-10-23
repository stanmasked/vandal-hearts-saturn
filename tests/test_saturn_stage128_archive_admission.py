"""Stage128: invented-only strict archival admission before original-disc Stage125."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_saturn_private_capture_archive_gate import archive_at
from tools.saturn_private_prologue_continue_tenth_c import (
    _enforce_stage124_capture_archive_integrity,
    run_private_prologue_continue_tenth_c,
)


class Stage128OriginalGameAdmissionTests(unittest.TestCase):
    def test_complete_synthetic_stage124_archive_passes_structure_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "invented-private-readback.tar.gz"
            size, digest = archive_at(archive, count=900)
            report = _enforce_stage124_capture_archive_integrity(
                archive, (size, digest, (1, 2, 3))
            )
            self.assertEqual(report["checkpoint_pngs"], 1800)
            self.assertEqual(report["regular_members"], 1816)
            self.assertFalse(report["drive_upload_and_readback_verified"])
            self.assertTrue(report["archive_matches_supplied_fingerprint"])

    def test_missing_checkpoint_must_fail_even_when_receipt_digest_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "incomplete-invented-readback.tar.gz"
            size, digest = archive_at(archive, count=900, omit=("control", 120))
            with self.assertRaisesRegex(ValueError, "checkpoint sequence incomplete"):
                _enforce_stage124_capture_archive_integrity(archive, (size, digest, ()))

    def test_broken_png_must_fail_even_when_sha_and_size_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "invented-bad-png.tar.gz"
            size, digest = archive_at(archive, count=900, invalid_png=True)
            with self.assertRaisesRegex(ValueError, "PNG"):
                _enforce_stage124_capture_archive_integrity(archive, (size, digest, ()))

    def test_bad_and_missing_fingerprints_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "invented-valid.tar.gz"
            size, digest = archive_at(archive, count=900)
            for fingerprint in ((size, "0" * 64), (size - 1, digest),
                                (0, digest), ("bad", digest), (size,), None):
                with self.subTest(fingerprint=str(fingerprint)[:45]):
                    with self.assertRaises((ValueError, TypeError)):
                        _enforce_stage124_capture_archive_integrity(archive, fingerprint)
            archive.unlink()
            with self.assertRaises(ValueError):
                _enforce_stage124_capture_archive_integrity(archive, (size, digest, ()))

    def test_stage125_runtime_stops_at_capture_integrity_before_looking_for_emulator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "tools.saturn_private_prologue_continue_tenth_c._require_stage124_drive_readback_receipt",
                return_value=(100, "a" * 64, ())
            ), patch(
                "tools.saturn_private_prologue_continue_tenth_c._enforce_stage124_capture_archive_integrity",
                side_effect=ValueError("STAGE128_ARCHIVE_INTEGRITY_REJECTED")
            ) as preflight:
                with self.assertRaisesRegex(ValueError, "STAGE128_ARCHIVE_INTEGRITY_REJECTED"):
                    run_private_prologue_continue_tenth_c(
                        root / "missing.cue", root / "track1.bin", root / "track2.bin",
                        root / "missing-runner", "0" * 64,
                        root / "control", root / "enabled",
                        root / "receipt.json", root / "readback.tar.gz"
                    )
                preflight.assert_called_once()


if __name__ == "__main__":
    unittest.main()
