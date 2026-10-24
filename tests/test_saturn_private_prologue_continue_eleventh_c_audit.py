"""Stage144 eleventh-C schedule and paired-capture audit tests; no game media."""
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from tools import saturn_private_prologue_continue_eleventh_c_audit as audit
from tools.saturn_private_prologue_continue_eleventh_c_audit import (
    FRAME_COUNT, CONFIRM11_PRESS, CONFIRM11_RELEASE, CHECKPOINTS,
    PRE_ELEVENTH_CHECKPOINTS, POST_ELEVENTH_BY_121200,
    DECA_EVENTS_132, DECA_STATE_132, ELEVA_EVENTS, ELEVA_STATE,
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, data: bytes = b"") -> bytes:
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def _png(rgb=(20, 30, 40), width=64, height=64) -> bytes:
    scanline = b"\0" + bytes(rgb) * width
    pixels = scanline * height
    return (PNG_SIGNATURE
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(pixels))
            + _chunk(b"IEND"))


def _write_private(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    path.chmod(0o600)


def _make_pair(root: Path, *, divergence_frame=120120, bad_pad=False, enabled_width=64):
    control, enabled = root / "control", root / "enabled"
    control.mkdir(mode=0o700)
    enabled.mkdir(mode=0o700)
    visible = _png((20, 30, 40))
    enabled_base = _png((20, 30, 40), width=enabled_width)
    changed = _png((90, 100, 110), width=enabled_width)
    _write_private(control / "pre.png", visible)
    _write_private(enabled / "pre.png", visible)
    _write_private(control / "post.png", visible)
    post_enabled = changed if (divergence_frame is not None and divergence_frame <= FRAME_COUNT) else enabled_base
    _write_private(enabled / "post.png", post_enabled)

    for frame in CHECKPOINTS:
        _write_private(control / f"frame-{frame}.png", visible)
        changed_now = divergence_frame is not None and frame >= divergence_frame
        _write_private(enabled / f"frame-{frame}.png", changed if changed_now else enabled_base)

    samples = [0] + list(CHECKPOINTS) + [FRAME_COUNT]
    for folder, width in ((control, 64), (enabled, enabled_width)):
        stats = (
            f"STAGE99_FRAMES {FRAME_COUNT}\n"
            "STAGE99_PC_BEFORE 0\n"
            "STAGE99_PC_AFTER 0\n"
            f"STAGE99_WIDTH {width}\n"
            "STAGE99_HEIGHT 64\n"
        ).encode("ascii")
        sh2 = "".join(f"VH_SH2 frame={n} pc=0 valid=1\n" for n in samples).encode("ascii")
        video = "".join(f"VH_VIDEO frame={n} pc=0\n" for n in samples).encode("ascii")
        _write_private(folder / "frames.stats", stats)
        _write_private(folder / "sh2-window.txt", sh2)
        _write_private(folder / "video-state.txt", video)
        _write_private(folder / "fad.vhcdlog", b"VHCD_FAD 123\nVHCD_FAD 456\n")
        _write_private(folder / "pad-events.txt",
                       ELEVA_EVENTS if folder == enabled else DECA_EVENTS_132)
        _write_private(folder / "pad-state.txt",
                       ELEVA_STATE if folder == enabled else DECA_STATE_132)
    if bad_pad:
        _write_private(enabled / "pad-events.txt",
                       ELEVA_EVENTS.replace(b"120000", b"120120", 1))
    return control, enabled


class EleventhCReceiptScheduleTests(unittest.TestCase):
    def test_control_has_shared_tenth_c_and_132000_footer(self):
        self.assertEqual(FRAME_COUNT, 132000)
        self.assertIn(b"VH_PAD frame=108000 button=C action=PRESS\n", DECA_EVENTS_132)
        self.assertIn(b"VH_PAD frame=108006 button=C action=RELEASE\n", DECA_EVENTS_132)
        self.assertIn(b"VH_PAD mode=1 completed_frames=132000\n", DECA_EVENTS_132)
        self.assertNotIn(b"VH_PAD frame=120000 button=C action=PRESS\n", DECA_EVENTS_132)

    def test_intervention_adds_only_eleventh_c_receipts(self):
        self.assertEqual(CONFIRM11_PRESS, 120000)
        self.assertEqual(CONFIRM11_RELEASE, 120006)
        self.assertIn(b"VH_PAD frame=120000 button=C action=PRESS\n", ELEVA_EVENTS)
        self.assertIn(b"VH_PAD frame=120006 button=C action=RELEASE\n", ELEVA_EVENTS)
        self.assertIn(b"VH_PADSTATE frame=120000 button=C active_low_bit=0\n", ELEVA_STATE)
        self.assertIn(b"VH_PADSTATE frame=120006 button=C active_low_bit=1\n", ELEVA_STATE)
        self.assertNotIn(b"VH_PAD frame=120000 button=C action=PRESS\n", DECA_EVENTS_132)
        self.assertNotIn(b"VH_PADSTATE frame=120000 button=C active_low_bit=0\n", DECA_STATE_132)

    def test_checkpoint_window_is_999_pre_and_101_post(self):
        self.assertEqual(len(CHECKPOINTS), 1100)
        self.assertEqual(len(PRE_ELEVENTH_CHECKPOINTS), 999)
        self.assertEqual(PRE_ELEVENTH_CHECKPOINTS[-1], 119880)
        self.assertEqual(len(CHECKPOINTS) - len(PRE_ELEVENTH_CHECKPOINTS), 101)

    def test_early_divergence_window_begins_after_eleventh_press(self):
        self.assertEqual(POST_ELEVENTH_BY_121200[0], 120120)
        self.assertEqual(POST_ELEVENTH_BY_121200[-1], 121200)
        self.assertEqual(len(POST_ELEVENTH_BY_121200), 10)


class EleventhCPairedCaptureAuditTests(unittest.TestCase):
    def test_valid_pair_proves_integrity_and_framebuffer_divergence_only(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td))
            result = audit.audit_private_prologue_continue_eleventh_c(control, enabled)
            self.assertEqual(result["frames_per_process"], 132000)
            self.assertEqual(result["checkpoint_png_count_per_process"], 1100)
            self.assertEqual(result["pre_eleventh_checkpoint_equal_count"], 999)
            self.assertEqual(result["pre_eleventh_checkpoint_total"], 999)
            self.assertEqual(result["eleventh_C_press_frame"], 120000)
            self.assertEqual(result["eleventh_C_release_frame"], 120006)
            self.assertEqual(result["first_post_eleventh_framebuffer_divergence_by_121200"], 120120)
            self.assertEqual(result["first_post_eleventh_framebuffer_divergence_through_132000"], 120120)
            self.assertTrue(result["frame_132000_differs"])
            self.assertFalse(result["first_battle_or_player_control_verified"])
            self.assertFalse(result["original_media_or_frame_hashes_exported"])

    def test_divergence_before_eleventh_c_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td), divergence_frame=119880)
            with self.assertRaisesRegex(ValueError, "diverged before eleventh C"):
                audit.audit_private_prologue_continue_eleventh_c(control, enabled)

    def test_no_post_press_framebuffer_effect_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td), divergence_frame=None)
            with self.assertRaisesRegex(ValueError, "no framebuffer effect"):
                audit.audit_private_prologue_continue_eleventh_c(control, enabled)

    def test_wrong_eleventh_c_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td), bad_pad=True)
            with self.assertRaisesRegex(ValueError, "eleventh-C event receipt mismatch"):
                audit.audit_private_prologue_continue_eleventh_c(control, enabled)

    def test_missing_checkpoint_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td))
            (enabled / "frame-120120.png").unlink()
            with self.assertRaisesRegex(ValueError, "output file set mismatch"):
                audit.audit_private_prologue_continue_eleventh_c(control, enabled)

    def test_mismatched_frame_dimensions_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td), enabled_width=80)
            with self.assertRaisesRegex(ValueError, "Stage144 PNG geometry changed"):
                audit.audit_private_prologue_continue_eleventh_c(control, enabled)

    def test_noncanonical_fad_log_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td))
            _write_private(enabled / "fad.vhcdlog", b"VHCD_FAD 123\nnot-a-fad\n")
            with self.assertRaisesRegex(ValueError, "nonnumeric entries"):
                audit.audit_private_prologue_continue_eleventh_c(control, enabled)

    def test_unexpected_output_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            control, enabled = _make_pair(Path(td))
            _write_private(enabled / "extra.txt", b"unexpected\n")
            with self.assertRaisesRegex(ValueError, "output file set mismatch"):
                audit.audit_private_prologue_continue_eleventh_c(control, enabled)


if __name__ == "__main__":
    unittest.main()
