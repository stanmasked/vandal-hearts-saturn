"""Synthetic-only Stage145 paired-capture audit tests; no game media."""
import struct
from pathlib import Path
import tempfile
import unittest
import zlib

from tools import saturn_private_prologue_continue_twelfth_c_audit as audit
from tools.saturn_private_prologue_continue_twelfth_c_audit import (
    FRAME_COUNT, CONFIRM12_PRESS, CONFIRM12_RELEASE, CHECKPOINTS,
    PRE_TWELFTH_CHECKPOINTS, POST_TWELFTH_BY_133200,
    CONTROL_EVENTS, CONTROL_STATE, TWELFTH_EVENTS, TWELFTH_STATE,
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, data: bytes = b"") -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)


def _png(rgb=(20, 30, 40), width=64, height=64) -> bytes:
    scanline = b"\0" + bytes(rgb) * width
    return (PNG_SIGNATURE + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(scanline * height)) + _chunk(b"IEND"))


def _write_private(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    path.chmod(0o600)


def _make_pair(root: Path, *, divergence_frame=132120, bad_pad=False, enabled_width=64):
    control, enabled = root / "control", root / "enabled"
    control.mkdir(mode=0o700)
    enabled.mkdir(mode=0o700)
    visible = _png((20, 30, 40))
    enabled_base = _png((20, 30, 40), width=enabled_width)
    changed = _png((90, 100, 110), width=enabled_width)
    _write_private(control / "pre.png", visible)
    _write_private(enabled / "pre.png", visible)
    _write_private(control / "post.png", visible)
    _write_private(enabled / "post.png", changed if divergence_frame is not None else enabled_base)
    for frame in CHECKPOINTS:
        _write_private(control / f"frame-{frame}.png", visible)
        is_changed = divergence_frame is not None and frame >= divergence_frame
        _write_private(enabled / f"frame-{frame}.png", changed if is_changed else enabled_base)
    samples = [0] + list(CHECKPOINTS) + [FRAME_COUNT]
    for folder, width in ((control, 64), (enabled, enabled_width)):
        _write_private(folder / "frames.stats", (
            f"STAGE99_FRAMES {FRAME_COUNT}\nSTAGE99_PC_BEFORE 0\nSTAGE99_PC_AFTER 0\n"
            f"STAGE99_WIDTH {width}\nSTAGE99_HEIGHT 64\n").encode("ascii"))
        _write_private(folder / "sh2-window.txt", "".join(f"VH_SH2 frame={n} pc=0 valid=1\n" for n in samples).encode())
        _write_private(folder / "video-state.txt", "".join(f"VH_VIDEO frame={n} pc=0\n" for n in samples).encode())
        _write_private(folder / "fad.vhcdlog", b"VHCD_FAD 123\nVHCD_FAD 456\n")
        _write_private(folder / "pad-events.txt", TWELFTH_EVENTS if folder == enabled else CONTROL_EVENTS)
        _write_private(folder / "pad-state.txt", TWELFTH_STATE if folder == enabled else CONTROL_STATE)
    if bad_pad:
        _write_private(enabled / "pad-events.txt", TWELFTH_EVENTS.replace(b"132000", b"132120", 1))
    return control, enabled


class TwelfthCReceiptScheduleTests(unittest.TestCase):
    def test_schedule_extends_to_144000_and_shares_eleventh_c(self):
        self.assertEqual(FRAME_COUNT, 144000)
        self.assertEqual(len(CHECKPOINTS), 1200)
        self.assertEqual(len(PRE_TWELFTH_CHECKPOINTS), 1099)
        self.assertEqual(PRE_TWELFTH_CHECKPOINTS[-1], 131880)
        self.assertEqual(CONFIRM12_PRESS, 132000)
        self.assertEqual(CONFIRM12_RELEASE, 132006)
        self.assertIn(b"VH_PAD frame=120000 button=C action=PRESS\n", CONTROL_EVENTS)
        self.assertIn(b"VH_PAD frame=120006 button=C action=RELEASE\n", CONTROL_EVENTS)
        self.assertNotIn(b"VH_PAD frame=132000 button=C action=PRESS\n", CONTROL_EVENTS)
        self.assertIn(b"VH_PAD frame=132000 button=C action=PRESS\n", TWELFTH_EVENTS)
        self.assertIn(b"VH_PAD frame=132006 button=C action=RELEASE\n", TWELFTH_EVENTS)

    def test_early_divergence_window_is_132120_through_133200(self):
        self.assertEqual(POST_TWELFTH_BY_133200[0], 132120)
        self.assertEqual(POST_TWELFTH_BY_133200[-1], 133200)
        self.assertEqual(len(POST_TWELFTH_BY_133200), 10)


class TwelfthCPairedCaptureAuditTests(unittest.TestCase):
    def test_valid_pair_proves_integrity_and_framebuffer_divergence_only(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td))
            result = audit.audit_private_prologue_continue_twelfth_c(control, enabled)
            self.assertEqual(result["frames_per_process"], 144000)
            self.assertEqual(result["checkpoint_png_count_per_process"], 1200)
            self.assertEqual(result["pre_twelfth_checkpoint_equal_count"], 1099)
            self.assertEqual(result["first_post_twelfth_framebuffer_divergence_by_133200"], 132120)
            self.assertEqual(result["first_post_twelfth_framebuffer_divergence_through_144000"], 132120)
            self.assertTrue(result["frame_144000_differs"])
            self.assertFalse(result["first_battle_or_player_control_verified"])
            self.assertFalse(result["original_media_or_frame_hashes_exported"])

    def test_divergence_before_twelfth_c_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td), divergence_frame=131880)
            with self.assertRaisesRegex(ValueError, "diverged before twelfth C"):
                audit.audit_private_prologue_continue_twelfth_c(control, enabled)

    def test_no_post_press_framebuffer_effect_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td), divergence_frame=None)
            with self.assertRaisesRegex(ValueError, "no framebuffer effect"):
                audit.audit_private_prologue_continue_twelfth_c(control, enabled)

    def test_wrong_twelfth_c_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td), bad_pad=True)
            with self.assertRaisesRegex(ValueError, "twelfth-C event receipt mismatch"):
                audit.audit_private_prologue_continue_twelfth_c(control, enabled)

    def test_missing_checkpoint_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td))
            (enabled / "frame-132120.png").unlink()
            with self.assertRaisesRegex(ValueError, "output file set mismatch"):
                audit.audit_private_prologue_continue_twelfth_c(control, enabled)

    def test_mismatched_frame_dimensions_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td), enabled_width=80)
            with self.assertRaisesRegex(ValueError, "checkpoint count/dimensions mismatch"):
                audit.audit_private_prologue_continue_twelfth_c(control, enabled)


if __name__ == "__main__":
    unittest.main()
