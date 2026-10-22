"""Stage108: ROM-free, synthetic-only pre-START baseline tests."""
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from tools.saturn_private_start_ab import CONTROL, START, FRAME_COUNT
from tools.saturn_private_start_baseline import (
    PRE_INPUT_FRAMES, POST_INPUT_FRAMES, audit_pre_start_equivalence,
)


def _chunk(kind: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + kind + data +
            struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))


def _fake_png(rgb: tuple[int, int, int], width: int = 64) -> bytes:
    height = 64
    lines = (b"\x00" + bytes(rgb) * width) * height
    return (b"\x89PNG\r\n\x1a\n" +
            _chunk(b"IHDR", struct.pack(">IIBBBBB",
                                        width, height, 8, 2, 0, 0, 0)) +
            _chunk(b"IDAT", zlib.compress(lines)) +
            _chunk(b"IEND", b""))


class PreStartBaselineTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        root.chmod(0o700)
        self.control, self.start = root / "control", root / "start"
        for directory, events, fads in (
            (self.control, CONTROL, b"VHCD_FAD 150\n"),
            (self.start, START, b"VHCD_FAD 150\nVHCD_FAD 151\n"),
        ):
            directory.mkdir(mode=0o700)
            self._write(directory, "pad-events.txt", events)
            self._write(directory, "fad.vhcdlog", fads)
            for frame in PRE_INPUT_FRAMES:
                self._write(directory, f"frame-{frame}.png",
                            _fake_png((11, 22, 33)))
            for frame in POST_INPUT_FRAMES:
                color = (44, 55, 66) if directory == self.control else (77, 88, 99)
                self._write(directory, f"frame-{frame}.png", _fake_png(color))

    @staticmethod
    def _write(directory: Path, name: str, data: bytes):
        out = directory / name
        out.write_bytes(data)
        out.chmod(0o600)

    def audit(self):
        return audit_pre_start_equivalence(self.control, self.start)

    def test_identical_preinput_and_changed_postinput_pass_as_files(self):
        result = self.audit()
        self.assertEqual(result["kind"],
                         "STAGE108_PRIVATE_START_PREINPUT_EQUIVALENCE_ONLY")
        self.assertEqual(result["pre_input_frames_compared"], [11880, 12000])
        self.assertTrue(result["pre_input_png_files_byte_identical"])
        self.assertTrue(result["post_input_12120_png_files_differ"])
        self.assertTrue(result["post_input_13200_png_files_differ"])
        self.assertEqual(result["intervention_start_press_frame"], 12060)
        self.assertEqual(result["intervention_start_release_frame"], 12066)
        self.assertFalse(result["post_input_difference_proves_game_reacted"])
        self.assertFalse(result["game_menu_visually_confirmed_by_this_auditor"])
        self.assertNotIn(str(self.control), str(result))

    def test_preinput_divergence_at_either_checkpoint_fails_closed(self):
        for frame in PRE_INPUT_FRAMES:
            file = self.start / f"frame-{frame}.png"
            original = file.read_bytes()
            with self.subTest(frame=frame):
                self._write(self.start, file.name, _fake_png((9, 8, 7)))
                with self.assertRaisesRegex(ValueError, "before the START pulse"):
                    self.audit()
                self._write(self.start, file.name, original)

    def test_missing_corrupt_and_world_readable_preinput_fail(self):
        file = self.start / "frame-12000.png"
        original = file.read_bytes()
        file.unlink()
        with self.assertRaises(OSError):
            self.audit()
        self._write(self.start, file.name, b"not PNG")
        with self.assertRaises(ValueError):
            self.audit()
        self._write(self.start, file.name, original)
        file.chmod(0o644)
        with self.assertRaises(ValueError):
            self.audit()

    def test_postinput_equality_is_not_a_synthetic_failure(self):
        for frame in POST_INPUT_FRAMES:
            target = f"frame-{frame}.png"
            self._write(self.start, target, (self.control / target).read_bytes())
        report = self.audit()
        self.assertFalse(report["post_input_12120_png_files_differ"])
        self.assertFalse(report["post_input_13200_png_files_differ"])
        self.assertFalse(report["game_menu_visually_confirmed_by_this_auditor"])

    def test_wrong_pad_receipt_rejected_by_inherited_stage107_gate(self):
        self._write(self.start, "pad-events.txt",
                    START.replace(b"frame=12060", b"frame=12000"))
        with self.assertRaises(ValueError):
            self.audit()

    def test_same_frame_resolution_mismatch_rejected(self):
        self._write(self.start, "frame-12120.png",
                    _fake_png((77, 88, 99), width=80))
        with self.assertRaisesRegex(ValueError, "dimensions differ"):
            self.audit()

    def test_symlinked_checkpoint_rejected(self):
        frame = self.start / "frame-11880.png"
        original = self.start / "orig.png"
        frame.rename(original)
        frame.symlink_to(original)
        with self.assertRaises((OSError, ValueError)):
            self.audit()


if __name__ == "__main__":
    unittest.main()
