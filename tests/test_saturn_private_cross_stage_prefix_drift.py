"""Synthetic-only decoded-pixel cross-stage drift audit tests."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from tools.saturn_private_cross_stage_prefix_drift import (
    CHECKPOINTS, audit_private_cross_stage_prefix_drift,
)


def _png(rgb, compress_level=6):
    image = Image.new("RGB", (64, 64), rgb)
    stream = BytesIO()
    image.save(stream, format="PNG", compress_level=compress_level)
    return stream.getvalue()


def _write(path: Path, data: bytes):
    path.write_bytes(data)
    path.chmod(0o600)


def _cohort(path: Path, base_png: bytes, changed_frames=(), *, compress_level=6):
    path.mkdir(mode=0o700)
    changed = _png((90, 100, 110), compress_level=compress_level)
    for frame in CHECKPOINTS:
        _write(path / f"frame-{frame}.png", changed if frame in changed_frames else base_png)


class CrossStagePrefixDriftTests(unittest.TestCase):
    def test_reports_decoded_pixel_drift_but_keeps_stage145_pair_stable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ref = _png((20, 30, 40))
            changed_frames = {7800, 96000}
            _cohort(root / "stage144", ref)
            _cohort(root / "stage145-control", ref, changed_frames)
            _cohort(root / "stage145-enabled", ref, changed_frames)
            result = audit_private_cross_stage_prefix_drift(
                root / "stage144", root / "stage145-control", root / "stage145-enabled",
            )
            self.assertEqual(result["checkpoint_count"], 800)
            self.assertEqual(result["stage145_control_enabled_equal_checkpoint_count"], 800)
            self.assertEqual(result["control_vs_stage144_pixel_mismatch_count"], 2)
            self.assertEqual(result["enabled_vs_stage144_pixel_mismatch_count"], 2)
            self.assertTrue(result["stage145_cross_stage_mismatch_sets_equal"])
            self.assertEqual(result["first_cross_stage_pixel_mismatch_frame"], 7800)
            self.assertEqual(result["last_cross_stage_pixel_mismatch_frame"], 96000)
            self.assertFalse(result["private_pixel_hashes_exported"])

    def test_png_encoding_changes_do_not_count_as_pixel_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _cohort(root / "stage144", _png((20, 30, 40), compress_level=1))
            _cohort(root / "stage145-control", _png((20, 30, 40), compress_level=9))
            _cohort(root / "stage145-enabled", _png((20, 30, 40), compress_level=6))
            result = audit_private_cross_stage_prefix_drift(
                root / "stage144", root / "stage145-control", root / "stage145-enabled",
            )
            self.assertEqual(result["control_vs_stage144_pixel_mismatch_count"], 0)
            self.assertEqual(result["enabled_vs_stage144_pixel_mismatch_count"], 0)

    def test_stage145_internal_prefix_divergence_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ref = _png((20, 30, 40))
            _cohort(root / "stage144", ref)
            _cohort(root / "stage145-control", ref)
            _cohort(root / "stage145-enabled", ref, {1200})
            with self.assertRaisesRegex(ValueError, "Stage145 cohorts differ within the pre-input prefix"):
                audit_private_cross_stage_prefix_drift(
                    root / "stage144", root / "stage145-control", root / "stage145-enabled",
                )


if __name__ == "__main__":
    unittest.main()
