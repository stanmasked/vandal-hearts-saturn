"""Stage112 synthetic-only tests for dual-START private evidence auditing."""
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from tools.saturn_private_original_start_sequence import (
    CONTROL_EVENTS, START_EVENTS, CONTROL_STATE, START_STATE,
    FRAME_COUNT, audit_private_start_sequence,
)


def _chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data +
            struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))


def _png(color):
    row = b"\x00" + bytes(color) * 64
    pixels = row * 64
    return (b"\x89PNG\r\n\x1a\n" +
            _chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0)) +
            _chunk(b"IDAT", zlib.compress(pixels)) +
            _chunk(b"IEND", b""))


class Stage112PrivateAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        root.chmod(0o700)
        self.control = root / "control"
        self.intervention = root / "intervention"
        self.control.mkdir(mode=0o700)
        self.intervention.mkdir(mode=0o700)
        self._populate(self.control, False)
        self._populate(self.intervention, True)

    @staticmethod
    def _write(folder, name, payload):
        path = folder / name
        path.write_bytes(payload)
        path.chmod(0o600)

    def _populate(self, folder, intervention):
        self._write(folder, "pad-events.txt",
                    START_EVENTS if intervention else CONTROL_EVENTS)
        self._write(folder, "pad-state.txt",
                    START_STATE if intervention else CONTROL_STATE)
        self._write(folder, "fad.vhcdlog", b"VHCD_FAD 150\n")
        self._write(folder, "pre.png", _png((25, 35, 45)))
        self._write(folder, "post.png", _png((25, 35, 45) if not intervention else (80, 90, 100)))
        self._write(folder, "frames.stats",
                    b"STAGE99_FRAMES 24000\nSTAGE99_PC_BEFORE 100\n"
                    b"STAGE99_PC_AFTER 200\nSTAGE99_WIDTH 64\nSTAGE99_HEIGHT 64\n")
        samples = [0] + list(range(120, FRAME_COUNT + 1, 120)) + [FRAME_COUNT]
        sh2 = "".join(
            f"VH_SH2 frame={n} pc=1 valid=1 sr=0 pr=0 gbr=0 r0=0 r1=0 r2=0 "
            f"r3=0 r4=0 r5=0 r15=0 m8=0 m6=0 m4=0 m2=0 op0=0 p2=0 p4=0 p6=0 p8=0\n"
            for n in samples
        ).encode("ascii")
        video = "".join(
            f"VH_VIDEO frame={n} pc=1 tvmd=0 bgon=0 ramctl=0 vdp1_tvmr=0 "
            f"vdp1_ptmr=0 vdp1_edsr=0 vdp1_nz=0 vdp2_nz=0 cram_nz=0 rgb_nz=0 width=64 height=64\n"
            for n in samples
        ).encode("ascii")
        self._write(folder, "sh2-window.txt", sh2)
        self._write(folder, "video-state.txt", video)
        for frame in range(120, FRAME_COUNT + 1, 120):
            # Same bytes before the first pulse; distinct title/menu evidence
            # after the first pulse. The audit does not label any scene as a battle.
            color = (25, 35, 45) if not intervention or frame < 12120 else (80, 90, 100)
            self._write(folder, f"frame-{frame}.png", _png(color))

    def test_accepts_complete_dual_pulse_integrity_evidence(self):
        result = audit_private_start_sequence(self.control, self.intervention)
        self.assertEqual(result["frames_per_process"], 24000)
        self.assertEqual(result["checkpoint_png_count_per_process"], 200)
        self.assertTrue(result["all_checkpoint_pngs_valid_and_sequential"])
        self.assertTrue(result["same_dimensions_and_pre_first_input_frames"])
        self.assertTrue(result["post_first_start_frame_files_differ_at_12120_and_13200"])
        self.assertTrue(result["both_active_low_start_press_and_release_pairs_verified"])
        self.assertFalse(result["first_tactical_battle_verified"])
        self.assertFalse(result["original_media_or_frame_hashes_exported"])

    def test_missing_intermediate_checkpoint_is_rejected(self):
        (self.intervention / "frame-600.png").unlink()
        with self.assertRaisesRegex(ValueError, "checkpoint sequence incomplete"):
            audit_private_start_sequence(self.control, self.intervention)

    def test_second_press_or_release_receipt_tampering_is_rejected(self):
        self._write(self.intervention, "pad-state.txt",
                    START_STATE.replace(b"frame=12246 start_bit=1", b"frame=12245 start_bit=1"))
        with self.assertRaisesRegex(ValueError, "active-low bit receipt mismatch"):
            audit_private_start_sequence(self.control, self.intervention)

    def test_pre_input_frame_divergence_is_rejected(self):
        self._write(self.intervention, "frame-12000.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "diverged before first input"):
            audit_private_start_sequence(self.control, self.intervention)

    def test_missing_post_start_frame_difference_is_rejected(self):
        for frame in (12120, 13200):
            self._write(self.intervention, f"frame-{frame}.png", _png((25, 35, 45)))
        with self.assertRaisesRegex(ValueError, "post-first-START A/B frame difference"):
            audit_private_start_sequence(self.control, self.intervention)


if __name__ == "__main__":
    unittest.main()
