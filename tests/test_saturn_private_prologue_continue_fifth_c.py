"""Synthetic-only tests for Stage119's private fifth-C paired audit."""
from pathlib import Path
import tempfile
import unittest

from test_saturn_private_original_start_triple import _png, _write
from tools.saturn_private_prologue_continue_fifth_c import (
    CHECKPOINTS, CONFIRM5_PRESS, CONFIRM5_RELEASE, FRAME_COUNT,
    PENTA_C_EVENTS, PENTA_C_STATE, QUAD_C_EVENTS_60K, QUAD_C_STATE_60K,
    audit_private_prologue_continue_fifth_c,
)

SAMPLES = [0] + list(CHECKPOINTS) + [FRAME_COUNT]


def _populate_60k(folder, fifth_c):
    _write(folder, "pad-events.txt", PENTA_C_EVENTS if fifth_c else QUAD_C_EVENTS_60K)
    _write(folder, "pad-state.txt", PENTA_C_STATE if fifth_c else QUAD_C_STATE_60K)
    _write(folder, "fad.vhcdlog", b"VHCD_FAD 150\n")
    _write(folder, "pre.png", _png((25, 35, 45)))
    _write(folder, "post.png", _png((210, 220, 230) if fifth_c else (180, 190, 200)))
    _write(
        folder,
        "frames.stats",
        b"STAGE99_FRAMES 60000\nSTAGE99_PC_BEFORE 100\n"
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
    for frame in CHECKPOINTS:
        if frame <= 12000:
            color = (25, 35, 45)
        elif frame <= 12240:
            color = (60, 70, 80)
        elif frame < 31200:
            color = (90, 100, 110)
        elif frame < 36000:
            color = (100, 110, 120)
        elif frame < 42000:
            color = (130, 140, 150)
        elif frame <= CONFIRM5_PRESS:
            color = (180, 190, 200)
        elif fifth_c:
            color = (210, 220, 230)
        else:
            color = (180, 190, 200)
        _write(folder, f"frame-{frame}.png", _png(color))


class Stage119PrivateDialogueAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o700)
        self.fourth_c = self.root / "fourth"
        self.fifth_c = self.root / "fifth_"
        for folder in (self.fourth_c, self.fifth_c):
            folder.mkdir(mode=0o700)
            folder.chmod(0o700)
        _populate_60k(self.fourth_c, False)
        _populate_60k(self.fifth_c, True)

    def test_accepts_fifth_c_effect_with_valid_60k_pair(self):
        report = audit_private_prologue_continue_fifth_c(self.fourth_c, self.fifth_c)
        self.assertEqual(report["frames_per_process"], 60000)
        self.assertEqual(report["checkpoint_png_count_per_process"], 500)
        self.assertEqual(report["fifth_C_press_frame"], CONFIRM5_PRESS)
        self.assertEqual(report["fifth_C_release_frame"], CONFIRM5_RELEASE)
        self.assertEqual(report["pre_fifth_checkpoint_equal_count"], 399)
        self.assertEqual(report["pre_fifth_checkpoint_total"], 399)
        self.assertTrue(report["all_pre_fifth_C_checkpoints_match"])
        self.assertEqual(report["first_post_fifth_C_framebuffer_divergence_by_49200"], 48120)
        self.assertTrue(report["frame_60000_differs"])
        self.assertFalse(report["first_battle_or_player_control_verified"])
        self.assertFalse(report["original_media_or_frame_hashes_exported"])

    def test_rejects_divergence_before_fifth_c(self):
        _write(self.fifth_c, "frame-47880.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "before fifth C confirm"):
            audit_private_prologue_continue_fifth_c(self.fourth_c, self.fifth_c)

    def test_rejects_no_fifth_c_effect_by_49200(self):
        for frame in CHECKPOINTS:
            if frame > CONFIRM5_PRESS:
                _write(
                    self.fifth_c, f"frame-{frame}.png",
                    (self.fourth_c / f"frame-{frame}.png").read_bytes(),
                )
        _write(self.fifth_c, "post.png", (self.fourth_c / "post.png").read_bytes())
        with self.assertRaisesRegex(ValueError, "no framebuffer effect by frame 49200"):
            audit_private_prologue_continue_fifth_c(self.fourth_c, self.fifth_c)

    def test_rejects_wrong_fifth_c_active_low_receipt(self):
        _write(
            self.fifth_c, "pad-state.txt",
            b"VH_PADSTATE frame=48000 button=C active_low_bit=1\n",
        )
        with self.assertRaisesRegex(ValueError, "fifth-C active-low receipt"):
            audit_private_prologue_continue_fifth_c(self.fourth_c, self.fifth_c)

    def test_rejects_missing_last_checkpoint(self):
        (self.fifth_c / "frame-60000.png").unlink()
        with self.assertRaisesRegex(ValueError, "file set mismatch"):
            audit_private_prologue_continue_fifth_c(self.fourth_c, self.fifth_c)

    def test_rejects_unequal_output_path_shape(self):
        with self.assertRaisesRegex(ValueError, "equal length"):
            audit_private_prologue_continue_fifth_c(
                self.fourth_c, self.root / "longer-fifth"
            )


if __name__ == "__main__":
    unittest.main()
