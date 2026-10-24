"""Invented-only tests for Stage143 PNG content quality; no original media."""
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from tools.saturn_stage143_visual_witness_gate import audit_visual_witness, _decode_is_black

SIG = b"\x89PNG\r\n\x1a\n"


def chunk(kind: bytes, payload: bytes = b"") -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)


def rgb_png(rgb=(30, 40, 50), width=352, height=240) -> bytes:
    row = b"\0" + bytes(rgb) * width
    raw = row * height
    return SIG + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND")


def gray1_png(value=0, width=352, height=240) -> bytes:
    packed = bytes([0x00 if value == 0 else 0xff]) * ((width + 7) // 8)
    raw = (b"\0" + packed) * height
    return SIG + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 1, 0, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND")

def palette_png(index=0, width=352, height=240, palette=b"\0\0\0\xff\0\0") -> bytes:
    raw = (b"\0" + bytes([index]) * width) * height
    return (SIG + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0))
            + chunk(b"PLTE", palette) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND"))


def rgb_png_with_invalid_late_filter() -> bytes:
    width, height = 352, 240
    row_bytes = width * 3
    raw = bytearray((b"\0" + bytes((30, 40, 50)) * width) * height)
    raw[row_bytes + 1] = 5  # Invalid filter on row 2, after a visibly non-black row.
    return (SIG + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND"))


class VisualWitnessTests(unittest.TestCase):
    def make_pair(self, root, control_black=(), enabled_black=(), *, count=4):
        a, b = root / "control", root / "enabled"
        a.mkdir(); b.mkdir()
        for folder, black_frames in ((a, set(control_black)), (b, set(enabled_black))):
            for frame in range(120, count * 120 + 1, 120):
                data = rgb_png((0, 0, 0)) if frame in black_frames else rgb_png()
                (folder / f"frame-{frame}.png").write_bytes(data)
        return a, b

    def test_visible_checkpoints_pass(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td))
            report = audit_visual_witness(a, b, through_frame=480)
            self.assertTrue(report["visual_witness_accepted"])
            self.assertEqual(report["checkpoint_pairs_decoded"], 4)

    def test_boot_black_prefix_is_allowed_if_display_later_appears(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), (120, 240), (120, 240))
            report = audit_visual_witness(a, b, through_frame=480)
            self.assertTrue(report["visual_witness_accepted"])
            self.assertEqual(report["control_black_prefix_count"], 2)

    def test_single_internal_black_checkpoint_is_review_required(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), (240,), (240,))
            report = audit_visual_witness(a, b, through_frame=480)
            self.assertFalse(report["visual_witness_accepted"])
            self.assertEqual(report["control_suspect_black_runs"], [{"first_frame": 240, "last_frame": 240, "count": 1}])

    def test_bounded_black_span_is_review_required(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), (240, 360), (240, 360))
            report = audit_visual_witness(a, b, through_frame=480)
            self.assertFalse(report["visual_witness_accepted"])
            self.assertEqual(report["enabled_suspect_black_runs"], [{"first_frame": 240, "last_frame": 360, "count": 2}])

    def test_trailing_black_span_is_review_required(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), (360, 480), (360, 480))
            report = audit_visual_witness(a, b, through_frame=480)
            self.assertFalse(report["visual_witness_accepted"])

    def test_all_black_capture_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), (120, 240, 360, 480), (120, 240, 360, 480))
            report = audit_visual_witness(a, b, through_frame=480)
            self.assertFalse(report["visual_witness_accepted"])
            self.assertEqual(report["control_suspect_black_runs"][0]["count"], 4)

    def test_different_black_masks_fail(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), (240,), (), count=4)
            report = audit_visual_witness(a, b, through_frame=480)
            self.assertFalse(report["black_classification_masks_match"])
            self.assertFalse(report["visual_witness_accepted"])

    def test_realistic_one_bit_all_black_png_is_detected(self):
        self.assertTrue(_decode_is_black(gray1_png(0)))
        self.assertFalse(_decode_is_black(gray1_png(1)))

    def test_palette_pixels_use_palette_rgb_not_palette_indices(self):
        self.assertTrue(_decode_is_black(palette_png(0)))
        self.assertFalse(_decode_is_black(palette_png(1)))

    def test_invalid_later_filter_fails_even_if_first_row_is_nonblack(self):
        with self.assertRaisesRegex(ValueError, "scanline filter invalid"):
            _decode_is_black(rgb_png_with_invalid_late_filter())

    def test_out_of_range_palette_index_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "pixel decode failed"):
            _decode_is_black(palette_png(2))

    def test_crc_corruption_fails_closed(self):
        blob = bytearray(rgb_png())
        blob[-7] ^= 1
        with self.assertRaisesRegex(ValueError, "CRC"):
            _decode_is_black(bytes(blob))

    def test_wrong_dimensions_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td))
            (a / "frame-120.png").write_bytes(rgb_png(width=320, height=240))
            with self.assertRaisesRegex(ValueError, "dimensions"):
                audit_visual_witness(a, b, through_frame=480)

    def test_missing_checkpoint_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td))
            (b / "frame-360.png").unlink()
            with self.assertRaisesRegex(ValueError, "missing or unsafe"):
                audit_visual_witness(a, b, through_frame=480)

    def test_symlinked_checkpoint_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td))
            p = b / "frame-360.png"
            p.unlink(); p.symlink_to(a / "frame-360.png")
            with self.assertRaisesRegex(ValueError, "missing or unsafe"):
                audit_visual_witness(a, b, through_frame=480)

    def test_explicitly_reviewed_black_spans_can_pass(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), (240, 360, 600), (240, 360, 600), count=6)
            report = audit_visual_witness(
                a, b, through_frame=720,
                reviewed_black_runs=((240, 360), (600, 600)),
            )
            self.assertTrue(report["visual_witness_accepted"])
            self.assertTrue(report["reviewed_black_runs_match_both_cohorts"])
            self.assertEqual(report["unreviewed_black_runs_control"], [])

    def test_partial_or_extra_allowlist_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), (240, 360), (240, 360), count=4)
            report = audit_visual_witness(a, b, through_frame=480,
                                          reviewed_black_runs=((240, 240),))
            self.assertFalse(report["visual_witness_accepted"])
            self.assertEqual(len(report["unreviewed_black_runs_control"]), 1)

    def test_reviewed_allowlist_cannot_hide_cohort_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), (240,), (), count=4)
            report = audit_visual_witness(a, b, through_frame=480,
                                          reviewed_black_runs=((240, 240),))
            self.assertFalse(report["black_classification_masks_match"])
            self.assertFalse(report["visual_witness_accepted"])

    def test_invalid_reviewed_ranges_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td), count=4)
            for ranges in (((241, 241),), ((240, 360), (360, 480)), ((600, 600),)):
                with self.subTest(ranges=ranges), self.assertRaises(ValueError):
                    audit_visual_witness(a, b, through_frame=480,
                                         reviewed_black_runs=ranges)

    def test_invalid_window_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.make_pair(Path(td))
            for frame in (0, 120, 241, 108000, -120):
                with self.subTest(frame=frame), self.assertRaises(ValueError):
                    audit_visual_witness(a, b, through_frame=frame)


if __name__ == "__main__":
    unittest.main()
