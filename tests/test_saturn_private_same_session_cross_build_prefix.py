"""Synthetic-only same-session Stage144/Stage145 prefix comparison tests."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from tools.saturn_private_same_session_cross_build_prefix import (
    CHECKPOINTS, DIAGNOSTIC_FRAMES, audit_private_same_session_cross_build_prefix,
)


def _png(rgb, compress_level=6):
    image = Image.new("RGB", (64, 64), rgb)
    stream = BytesIO()
    image.save(stream, format="PNG", compress_level=compress_level)
    return stream.getvalue()


def _write(path: Path, data: bytes):
    path.write_bytes(data)
    path.chmod(0o600)


def _cohort(path: Path, base_png: bytes, changed_frames=(), *, sh2_diff_frames=(), video_diff_frames=(), fad_lines=None):
    path.mkdir(mode=0o700)
    changed = _png((90, 100, 110))
    for frame in CHECKPOINTS:
        _write(path / f"frame-{frame}.png", changed if frame in changed_frames else base_png)
    sh2 = []
    video = []
    for frame in DIAGNOSTIC_FRAMES:
        sh2.append(f"VH_SH2 frame={frame} pc={2 if frame in sh2_diff_frames else 1}\n")
        video.append(f"VH_VIDEO frame={frame} pc={2 if frame in video_diff_frames else 1}\n")
    _write(path / "sh2-window.txt", "".join(sh2).encode("ascii"))
    _write(path / "video-state.txt", "".join(video).encode("ascii"))
    _write(path / "fad.vhcdlog", ("".join(f"VHCD_FAD {n}\n" for n in (fad_lines or [150, 151, 152]))).encode("ascii"))


class SameSessionCrossBuildPrefixTests(unittest.TestCase):
    def test_equal_prefix_returns_zero_mismatches(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            png = _png((20, 30, 40))
            _cohort(root / "stage144", png)
            _cohort(root / "stage145", png, fad_lines=[150, 151, 152])
            result = audit_private_same_session_cross_build_prefix(root / "stage144", root / "stage145")
            self.assertEqual(result["checkpoint_count"], 800)
            self.assertEqual(result["pixel_mismatch_count"], 0)
            self.assertIsNone(result["first_pixel_mismatch_frame"])
            self.assertEqual(result["sh2_diagnostic_record_mismatch_count"], 0)
            self.assertEqual(result["video_diagnostic_record_mismatch_count"], 0)
            self.assertEqual(result["fad_common_prefix_record_count"], 3)
            self.assertFalse(result["private_pixel_hashes_exported"])

    def test_reports_pixel_and_diagnostic_mismatches_without_hashes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            png = _png((20, 30, 40))
            changed = {7800, 96000}
            _cohort(root / "stage144", png)
            _cohort(root / "stage145", png, changed_frames=changed,
                    sh2_diff_frames={120}, video_diff_frames={0}, fad_lines=[150, 151])
            result = audit_private_same_session_cross_build_prefix(root / "stage144", root / "stage145")
            self.assertEqual(result["pixel_mismatch_count"], 2)
            self.assertEqual(result["first_pixel_mismatch_frame"], 7800)
            self.assertEqual(result["last_pixel_mismatch_frame"], 96000)
            self.assertEqual(result["pixel_mismatch_ranges"], [
                {"start_frame": 7800, "end_frame": 7800, "checkpoint_count": 1},
                {"start_frame": 96000, "end_frame": 96000, "checkpoint_count": 1},
            ])
            self.assertEqual(result["sh2_diagnostic_record_mismatch_count"], 1)
            self.assertEqual(result["first_sh2_diagnostic_mismatch_frame"], 120)
            self.assertEqual(result["video_diagnostic_record_mismatch_count"], 1)
            self.assertEqual(result["first_video_diagnostic_mismatch_frame"], 0)
            self.assertEqual(result["fad_common_prefix_record_count"], 2)
            self.assertFalse(result["original_media_or_frame_hashes_exported"])

    def test_png_encoding_difference_is_not_pixel_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _cohort(root / "stage144", _png((20, 30, 40), compress_level=1))
            _cohort(root / "stage145", _png((20, 30, 40), compress_level=9))
            result = audit_private_same_session_cross_build_prefix(root / "stage144", root / "stage145")
            self.assertEqual(result["pixel_mismatch_count"], 0)

    def test_missing_checkpoint_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            png = _png((20, 30, 40))
            _cohort(root / "stage144", png)
            _cohort(root / "stage145", png)
            (root / "stage145" / "frame-96000.png").unlink()
            with self.assertRaisesRegex(ValueError, "checkpoint set incomplete"):
                audit_private_same_session_cross_build_prefix(root / "stage144", root / "stage145")

    def test_same_directory_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _cohort(root / "stage144", _png((20, 30, 40)))
            with self.assertRaisesRegex(ValueError, "two distinct run directories"):
                audit_private_same_session_cross_build_prefix(root / "stage144", root / "stage144")


if __name__ == "__main__":
    unittest.main()
