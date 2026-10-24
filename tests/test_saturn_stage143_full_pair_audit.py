"""Synthetic-only regressions for the Stage143 full-pair visual audit helper."""
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from tools.saturn_stage143_full_pair_audit import audit_visual_checkpoint_pair

SIG = b"\x89PNG\r\n\x1a\n"


def chunk(kind: bytes, payload: bytes = b"") -> bytes:
    return (struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))


def rgb_png(rgb=(30, 40, 50), width=352, height=240) -> bytes:
    row = b"\0" + bytes(rgb) * width
    raw = row * height
    return (SIG + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND"))


class FullPairVisualAuditTests(unittest.TestCase):
    def make_pair(self, root: Path, control_black=(), enabled_black=(), *, count=4):
        a, b = root / "control", root / "enabled"
        a.mkdir(mode=0o700); b.mkdir(mode=0o700)
        for folder, black_frames in ((a, set(control_black)), (b, set(enabled_black))):
            for frame in range(120, count * 120 + 1, 120):
                data = rgb_png((0, 0, 0)) if frame in black_frames else rgb_png()
                (folder / f"frame-{frame}.png").write_bytes(data)
        return a, b

    def test_identical_visible_pair_passes(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td))
            r = audit_visual_checkpoint_pair(a, b, through_frame=480)
            self.assertTrue(r["visual_witness_accepted"])
            self.assertEqual(r["byte_identical_checkpoint_pair_count"], 4)
            self.assertEqual(r["byte_different_checkpoint_pair_count"], 0)

    def test_exact_reviewed_internal_black_span_passes(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), (240, 360), (240, 360))
            r = audit_visual_checkpoint_pair(a, b, through_frame=480,
                                             reviewed_black_runs=((240, 360),))
            self.assertTrue(r["visual_witness_accepted"])
            self.assertTrue(r["reviewed_black_runs_match_both_cohorts"])

    def test_unreviewed_internal_black_span_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), (240,), (240,))
            r = audit_visual_checkpoint_pair(a, b, through_frame=480)
            self.assertFalse(r["visual_witness_accepted"])
            self.assertEqual(r["control_black_runs"],
                             [{"first_frame": 240, "last_frame": 240, "count": 1}])

    def test_cohort_black_mask_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), (240,), ())
            r = audit_visual_checkpoint_pair(a, b, through_frame=480,
                                             reviewed_black_runs=((240, 240),))
            self.assertFalse(r["black_classification_masks_match"])
            self.assertFalse(r["visual_witness_accepted"])

    def test_missing_checkpoint_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td))
            (b / "frame-360.png").unlink()
            with self.assertRaisesRegex(ValueError, "sequence missing"):
                audit_visual_checkpoint_pair(a, b, through_frame=480)

    def test_symlinked_checkpoint_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td))
            p = b / "frame-360.png"
            p.unlink(); p.symlink_to(a / "frame-360.png")
            with self.assertRaisesRegex(ValueError, "unsafe"):
                audit_visual_checkpoint_pair(a, b, through_frame=480)

    def test_malformed_checkpoint_name_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td))
            (a / "frame-abc.png").write_bytes(rgb_png())
            with self.assertRaisesRegex(ValueError, "malformed checkpoint"):
                audit_visual_checkpoint_pair(a, b, through_frame=480)

    def test_corrupt_png_crc_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td))
            blob = bytearray((a / "frame-120.png").read_bytes())
            blob[-7] ^= 1
            (a / "frame-120.png").write_bytes(blob)
            with self.assertRaisesRegex(ValueError, "CRC"):
                audit_visual_checkpoint_pair(a, b, through_frame=480)

    def test_all_black_pair_never_passes(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), (120, 240, 360, 480), (120, 240, 360, 480))
            r = audit_visual_checkpoint_pair(a, b, through_frame=480,
                                             reviewed_black_runs=((120, 480),))
            self.assertFalse(r["visual_witness_accepted"])

    def test_reviewed_spans_must_be_valid_and_nonoverlapping(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td))
            for spans in (((121, 121),), ((240, 360), (360, 480)), ((600, 600),)):
                with self.subTest(spans=spans), self.assertRaises(ValueError):
                    audit_visual_checkpoint_pair(a, b, through_frame=480,
                                                 reviewed_black_runs=spans)


if __name__ == "__main__":
    unittest.main()
