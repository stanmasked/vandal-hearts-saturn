"""Synthetic-only tests for the Stage115 48,000-frame private audit."""
from pathlib import Path
import tempfile
import unittest

from test_saturn_private_original_start_triple import _png, _write
from tools.saturn_private_first_battle_window import (
    CONFIRM_EVENTS, CONFIRM_STATE, FIRST_ONLY_EVENTS, FIRST_ONLY_STATE,
    FRAME_COUNT, audit_private_first_battle_window,
)
from tools.saturn_private_original_start_sequence import FIRST_PRESS, FIRST_RELEASE

SAMPLES = [0] + list(range(120, FRAME_COUNT + 1, 120)) + [FRAME_COUNT]


def _populate(folder, confirm):
    _write(folder, "pad-events.txt", CONFIRM_EVENTS if confirm else FIRST_ONLY_EVENTS)
    _write(folder, "pad-state.txt", CONFIRM_STATE if confirm else FIRST_ONLY_STATE)
    _write(folder, "fad.vhcdlog", b"VHCD_FAD 150\n")
    _write(folder, "pre.png", _png((25, 35, 45)))
    _write(folder, "post.png", _png((90, 100, 110) if confirm else (15, 15, 15)))
    _write(
        folder,
        "frames.stats",
        b"STAGE99_FRAMES 48000\nSTAGE99_PC_BEFORE 100\n"
        b"STAGE99_PC_AFTER 200\nSTAGE99_WIDTH 64\nSTAGE99_HEIGHT 64\n",
    )
    sh2 = "".join(
        f"VH_SH2 frame={n} pc=1 valid=1 sr=0 pr=0 gbr=0 r0=0 r1=0 r2=0 "
        f"r3=0 r4=0 r5=0 r15=0 m8=0 m6=0 m4=0 m2=0\n"
        for n in SAMPLES
    ).encode("ascii")
    video = "".join(
        f"VH_VIDEO frame={n} pc=1 tvmd=0 bgon=0 ramctl=0 vdp1_tvmr=0 "
        f"vdp1_ptmr=0 vdp1_edsr=0 vdp1_nz=0 vdp2_nz=0 cram_nz=0 "
        f"rgb_nz=0 width=64 height=64\n"
        for n in SAMPLES
    ).encode("ascii")
    _write(folder, "sh2-window.txt", sh2)
    _write(folder, "video-state.txt", video)
    for frame in range(120, FRAME_COUNT + 1, 120):
        if frame <= 12000:
            color = (25, 35, 45)
        elif frame <= 12240:
            color = (60, 70, 80)
        elif confirm:
            color = (90, 100, 110)
        else:
            color = (60, 70, 80) if frame < 13680 else (15, 15, 15)
        _write(folder, f"frame-{frame}.png", _png(color))


class Stage115PrivateBattleWindowAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o700)
        self.first_only = self.root / "first-only"
        self.confirm_c = self.root / "confirm-c"
        for folder in (self.first_only, self.confirm_c):
            folder.mkdir(mode=0o700)
            folder.chmod(0o700)
        _populate(self.first_only, False)
        _populate(self.confirm_c, True)

    def test_accepts_400_checkpoint_pair_with_c_confirm(self):
        report = audit_private_first_battle_window(self.first_only, self.confirm_c)
        self.assertEqual(report["frames_per_process"], 48000)
        self.assertEqual(report["checkpoint_png_count_per_process"], 400)
        self.assertEqual(report["first_c_confirm_divergence_before_idle_attract_transition"], 12360)
        self.assertTrue(report["frame_24000_differs_from_first_start_only_control"])
        self.assertTrue(report["frame_48000_differs_from_first_start_only_control"])
        self.assertFalse(report["first_battle_or_player_control_verified"])
        self.assertFalse(report["original_media_or_frame_hashes_exported"])

    def test_rejects_no_confirm_effect_before_idle_attract_transition(self):
        for frame in range(12360, 13680, 120):
            _write(
                self.confirm_c,
                f"frame-{frame}.png",
                (self.first_only / f"frame-{frame}.png").read_bytes(),
            )
        with self.assertRaisesRegex(ValueError, "before the idle attract transition"):
            audit_private_first_battle_window(self.first_only, self.confirm_c)

    def test_rejects_divergence_before_confirm_pulse(self):
        _write(self.confirm_c, "frame-12120.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "before C confirm"):
            audit_private_first_battle_window(self.first_only, self.confirm_c)

    def test_rejects_missing_last_checkpoint(self):
        (self.confirm_c / "frame-48000.png").unlink()
        with self.assertRaisesRegex(ValueError, "file set mismatch"):
            audit_private_first_battle_window(self.first_only, self.confirm_c)

    def test_rejects_wrong_c_active_low_receipt(self):
        _write(self.confirm_c, "pad-state.txt", b"VH_PADSTATE frame=12240 button=C active_low_bit=1\n")
        with self.assertRaisesRegex(ValueError, "C-confirm active-low receipt"):
            audit_private_first_battle_window(self.first_only, self.confirm_c)


if __name__ == "__main__":
    unittest.main()
