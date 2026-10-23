"""Stage129: invented-only archive replay audit; no original Saturn media."""
import hashlib
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from test_saturn_private_prologue_continue_ninth_c import _run, _png
from tools.saturn_private_archived_pair_audit import audit_archived_stage124_pair
from tools.saturn_private_prologue_continue_ninth_c import OCTA_EVENTS_108


def _archive_pair(root: Path, mutate=None):
    a, b = root / "capture1", root / "capture2"
    _run(a, False)
    _run(b, True)
    if mutate is not None:
        mutate(a, b)
    path = root / "private-invented-only.tar.gz"
    with tarfile.open(path, "w:gz") as output:
        # Misleading folder names must NOT determine control/enabled roles.
        for folder, name in ((a, "d1"), (b, "d2")):
            for item in sorted(folder.iterdir()):
                output.add(item, arcname=f"arbitrary-prefix/{name}/{item.name}", recursive=False)
    return path, path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()


class Stage129PrivateArchiveReplayAuditTests(unittest.TestCase):
    def test_full_synthetic_pair_semantics_pass_not_authenticity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, size, digest = _archive_pair(Path(tmp))
            report = audit_archived_stage124_pair(
                path, expected_size=size, expected_sha256=digest)
            self.assertTrue(report["stage124_paired_capture_semantics_verified_in_archive"])
            self.assertEqual(report["pre_ninth_checkpoints_equal"], 799)
            self.assertFalse(report["historical_archive_provenance_authenticated"])
            self.assertFalse(report["owner_only_drive_readback_authenticated"])
            self.assertFalse(report["original_gameplay_or_battle_verified"])

    def test_invalid_ninth_c_receipt_rejected_despite_matching_tar_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            def mutate(_, enabled):
                (enabled / "pad-events.txt").write_bytes(OCTA_EVENTS_108)
            path, size, digest = _archive_pair(Path(tmp), mutate)
            with self.assertRaisesRegex(ValueError, "PAD receipt"):
                audit_archived_stage124_pair(path, expected_size=size,
                                             expected_sha256=digest)

    def test_before_ninth_frame_difference_rejected_despite_matching_tar_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            def mutate(_, enabled):
                (enabled / "frame-95880.png").write_bytes(_png(2))
            path, size, digest = _archive_pair(Path(tmp), mutate)
            with self.assertRaisesRegex(ValueError, "diverged before ninth C"):
                audit_archived_stage124_pair(path, expected_size=size,
                                             expected_sha256=digest)

    def test_stage125_does_not_reach_original_runner_when_semantics_fail(self):
        from tools.saturn_private_prologue_continue_tenth_c import (
            run_private_prologue_continue_tenth_c,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "tools.saturn_private_prologue_continue_tenth_c._require_stage124_drive_readback_receipt",
                return_value=(100, "a"*64, ())
            ), patch(
                "tools.saturn_private_prologue_continue_tenth_c._enforce_stage124_capture_archive_integrity",
                return_value={"checkpoint_pngs":1800}
            ), patch(
                "tools.saturn_private_prologue_continue_tenth_c.audit_archived_stage124_pair",
                side_effect=ValueError("STAGE129_SEMANTIC_FAIL")
            ) as paired:
                with self.assertRaisesRegex(ValueError, "STAGE129_SEMANTIC_FAIL"):
                    run_private_prologue_continue_tenth_c(
                        root/"missing.cue", root/"missing1.bin", root/"missing2.bin",
                        root/"missing-executable", "0"*64,
                        root/"control", root/"enabled", root/"receipt.json",
                        root/"downloaded.tar.gz")
                paired.assert_called_once()

    def test_missing_archive_never_claims_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "archive-not-present.tar.gz"
            with self.assertRaises(ValueError):
                audit_archived_stage124_pair(
                    missing, expected_size=100, expected_sha256="0"*64)


if __name__ == "__main__":
    unittest.main()
