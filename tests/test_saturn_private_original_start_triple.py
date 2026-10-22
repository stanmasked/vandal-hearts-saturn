"""Synthetic-only regressions for Stage113's three-way START experiment."""
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from tools.saturn_private_original_start_sequence import (
    CONTROL_EVENTS, CONTROL_STATE, FRAME_COUNT, FIRST_PRESS, FIRST_RELEASE,
    START_EVENTS, START_STATE,
)
from tools.saturn_private_original_start_triple import (
    FIRST_ONLY_EVENTS, FIRST_ONLY_STATE, audit_private_start_triple,
)


def _chunk(kind, data):
    return (
        struct.pack(">I", len(data)) + kind + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    )


def _png(color):
    row = b"\x00" + bytes(color) * 64
    pixels = row * 64
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(pixels))
        + _chunk(b"IEND", b"")
    )


def _write(folder, name, payload):
    path = folder / name
    path.write_bytes(payload)
    path.chmod(0o600)
    return path


class Stage113TripleStartAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o700)
        self.no_input = self.root / "no-input"
        self.first_only = self.root / "first-only"
        self.dual_start = self.root / "dual-start"
        for folder in (self.no_input, self.first_only, self.dual_start):
            folder.mkdir(mode=0o700)
            folder.chmod(0o700)
        self._populate(self.no_input, "no_input")
        self._populate(self.first_only, "first_only")
        self._populate(self.dual_start, "dual_start")

    def _populate(self, folder, mode):
        if mode == "no_input":
            events, state = CONTROL_EVENTS, CONTROL_STATE
        elif mode == "first_only":
            events, state = FIRST_ONLY_EVENTS, FIRST_ONLY_STATE
        else:
            events, state = START_EVENTS, START_STATE
        _write(folder, "pad-events.txt", events)
        _write(folder, "pad-state.txt", state)
        _write(folder, "fad.vhcdlog", b"VHCD_FAD 150\n")
        _write(folder, "pre.png", _png((25, 35, 45)))
        final_color = {
            "no_input": (15, 15, 15),
            "first_only": (60, 70, 80),
            "dual_start": (90, 100, 110),
        }[mode]
        _write(folder, "post.png", _png(final_color))
        _write(
            folder,
            "frames.stats",
            b"STAGE99_FRAMES 24000\nSTAGE99_PC_BEFORE 100\n"
            b"STAGE99_PC_AFTER 200\nSTAGE99_WIDTH 64\nSTAGE99_HEIGHT 64\n",
        )
        samples = [0] + list(range(120, FRAME_COUNT + 1, 120)) + [FRAME_COUNT]
        sh2 = "".join(
            f"VH_SH2 frame={n} pc=1 valid=1 sr=0 pr=0 gbr=0 r0=0 r1=0 r2=0 "
            f"r3=0 r4=0 r5=0 r15=0 m8=0 m6=0 m4=0 m2=0\n"
            for n in samples
        ).encode("ascii")
        video = "".join(
            f"VH_VIDEO frame={n} pc=1 tvmd=0 bgon=0 ramctl=0 vdp1_tvmr=0 "
            f"vdp1_ptmr=0 vdp1_edsr=0 vdp1_nz=0 vdp2_nz=0 cram_nz=0 "
            f"rgb_nz=0 width=64 height=64\n"
            for n in samples
        ).encode("ascii")
        _write(folder, "sh2-window.txt", sh2)
        _write(folder, "video-state.txt", video)

        for frame in range(120, FRAME_COUNT + 1, 120):
            if frame <= 12000:
                color = (25, 35, 45)
            elif mode == "no_input":
                color = (15, 15, 15)
            elif frame <= 12240:
                color = (60, 70, 80)
            elif mode == "first_only":
                color = (60, 70, 80)
            else:
                color = (90, 100, 110)
            _write(folder, f"frame-{frame}.png", _png(color))

    def test_three_way_run_isolates_second_start_response(self):
        report = audit_private_start_triple(
            self.no_input, self.first_only, self.dual_start
        )
        self.assertEqual(report["independent_cold_boot_processes"], 3)
        self.assertEqual(report["pre_first_start_checkpoints_compared"], 100)
        self.assertTrue(report["all_runs_identical_before_first_start"])
        self.assertEqual(report["first_only_and_dual_identical_through_frame"], 12120)
        self.assertTrue(report["first_start_menu_difference_verified_at_12120_and_13200"])
        self.assertEqual(report["second_start_first_measurable_frame_difference"], 12360)
        self.assertEqual(len(report["second_start_post_input_frames_compared"]), 98)
        self.assertFalse(report["first_tactical_battle_verified"])
        self.assertFalse(report["original_media_or_frame_hashes_exported"])

    def test_rejects_divergence_before_first_start(self):
        _write(self.first_only, "frame-12000.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "before the first START"):
            audit_private_start_triple(
                self.no_input, self.first_only, self.dual_start
            )

    def test_rejects_divergence_before_second_start(self):
        _write(self.dual_start, "frame-12120.png", _png((4, 5, 6)))
        with self.assertRaisesRegex(ValueError, "before the second START"):
            audit_private_start_triple(
                self.no_input, self.first_only, self.dual_start
            )

    def test_rejects_second_start_without_any_post_input_difference(self):
        for frame in range(12360, FRAME_COUNT + 1, 120):
            _write(
                self.dual_start,
                f"frame-{frame}.png",
                (self.first_only / f"frame-{frame}.png").read_bytes(),
            )
        with self.assertRaisesRegex(ValueError, "no measurable post-input"):
            audit_private_start_triple(
                self.no_input, self.first_only, self.dual_start
            )

    def test_rejects_missing_checkpoint(self):
        (self.dual_start / "frame-240.png").unlink()
        with self.assertRaisesRegex(ValueError, "checkpoint sequence incomplete"):
            audit_private_start_triple(
                self.no_input, self.first_only, self.dual_start
            )

    def test_rejects_tampered_second_pulse_receipt(self):
        _write(self.dual_start, "pad-state.txt", b"VH_PADSTATE frame=12240 start_bit=1\n")
        with self.assertRaisesRegex(ValueError, "dual-start active-low receipt"):
            audit_private_start_triple(
                self.no_input, self.first_only, self.dual_start
            )


if __name__ == "__main__":
    unittest.main()
