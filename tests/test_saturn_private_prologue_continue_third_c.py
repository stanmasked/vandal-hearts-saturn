"""Synthetic-only tests for Stage117's private third-C dialogue audit."""
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from test_saturn_private_original_start_triple import _png, _write
from tools.saturn_private_first_battle_window import FRAME_COUNT
from tools.saturn_private_prologue_continue_third_c import (
    CONFIRM3_PRESS, CONFIRM3_RELEASE, DOUBLE_C_EVENTS, DOUBLE_C_STATE,
    TRIPLE_C_EVENTS, TRIPLE_C_STATE, audit_private_prologue_continue_third_c,
    _run_one,
)

SAMPLES = [0] + list(range(120, FRAME_COUNT + 1, 120)) + [FRAME_COUNT]


def _populate(folder, triple_c):
    _write(folder, "pad-events.txt", TRIPLE_C_EVENTS if triple_c else DOUBLE_C_EVENTS)
    _write(folder, "pad-state.txt", TRIPLE_C_STATE if triple_c else DOUBLE_C_STATE)
    _write(folder, "fad.vhcdlog", b"VHCD_FAD 150\n")
    _write(folder, "pre.png", _png((25, 35, 45)))
    _write(folder, "post.png", _png((130, 140, 150) if triple_c else (90, 100, 110)))
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
        elif frame < CONFIRM3_PRESS + 120:
            # Both runs share START and two C presses; they must match until
            # the third-C intervention at frame 36000.
            color = (90, 100, 110)
        elif triple_c:
            color = (130, 140, 150)
        else:
            color = (90, 100, 110)
        _write(folder, f"frame-{frame}.png", _png(color))


class Stage117PrivateDialogueAuditTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o700)
        self.double_c = self.root / "double-c"
        self.triple_c = self.root / "triple-c"
        for folder in (self.double_c, self.triple_c):
            folder.mkdir(mode=0o700)
            folder.chmod(0o700)
        _populate(self.double_c, False)
        _populate(self.triple_c, True)

    def test_accepts_third_c_effect_with_valid_48k_pair(self):
        report = audit_private_prologue_continue_third_c(self.double_c, self.triple_c)
        self.assertEqual(report["frames_per_process"], 48000)
        self.assertEqual(report["third_C_press_frame"], CONFIRM3_PRESS)
        self.assertEqual(report["third_C_release_frame"], CONFIRM3_RELEASE)
        self.assertEqual(report["pre_third_checkpoint_equal_count"], 299)
        self.assertEqual(report["pre_third_checkpoint_total"], 299)
        self.assertTrue(report["all_pre_third_C_checkpoints_match"])
        self.assertEqual(report["first_post_third_C_framebuffer_divergence_by_42000"], 36120)
        self.assertTrue(report["frame_38400_differs_after_third_C"])
        self.assertFalse(report["first_battle_or_player_control_verified"])
        self.assertFalse(report["original_media_or_frame_hashes_exported"])

    def test_rejects_pre_third_c_divergence(self):
        _write(self.triple_c, "frame-30000.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "diverged before third C confirm"):
            audit_private_prologue_continue_third_c(self.double_c, self.triple_c)

    def test_rejects_no_third_c_effect_by_frame_42000(self):
        for frame in range(CONFIRM3_PRESS + 120, 42000 + 1, 120):
            _write(
                self.triple_c,
                f"frame-{frame}.png",
                (self.double_c / f"frame-{frame}.png").read_bytes(),
            )
        with self.assertRaisesRegex(ValueError, "no framebuffer effect by frame 42000"):
            audit_private_prologue_continue_third_c(self.double_c, self.triple_c)

    def test_rejects_wrong_third_c_active_low_receipt(self):
        _write(
            self.triple_c,
            "pad-state.txt",
            TRIPLE_C_STATE.replace(
                b"frame=36006 button=C active_low_bit=1",
                b"frame=36005 button=C active_low_bit=1",
            ),
        )
        with self.assertRaisesRegex(ValueError, "third-C active-low receipt mismatch"):
            audit_private_prologue_continue_third_c(self.double_c, self.triple_c)

    def test_rejects_missing_last_checkpoint(self):
        (self.triple_c / "frame-48000.png").unlink()
        with self.assertRaisesRegex(ValueError, "file set mismatch"):
            audit_private_prologue_continue_third_c(self.double_c, self.triple_c)


class Stage117PairedRunScheduleTests(unittest.TestCase):
    def test_both_runs_receive_same_scheduled_third_c_frame(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            control = root / "control"
            triple = root / "triple"
            control.mkdir(mode=0o700)
            triple.mkdir(mode=0o700)
            envs = []
            for folder, third_c in ((control, False), (triple, True)):
                process = Mock()
                process.wait.return_value = 0
                with patch(
                    "tools.saturn_private_prologue_continue_third_c.subprocess.Popen",
                    return_value=process,
                ) as popen:
                    _run_one(
                        Path("/private/yabause"),
                        Path("/private/original.cue"),
                        folder,
                        third_c=third_c,
                        seconds=5,
                    )
                envs.append(popen.call_args.kwargs["env"])
            self.assertEqual(
                envs[0]["VH_SATURN_CONFIRM_AT_FRAME3"],
                envs[1]["VH_SATURN_CONFIRM_AT_FRAME3"],
            )
            self.assertEqual(envs[0]["VH_SATURN_CONFIRM_AT_FRAME3"], str(CONFIRM3_PRESS))
            self.assertEqual(envs[0]["VH_SATURN_CONFIRM2_ENABLED"], "1")
            self.assertEqual(envs[1]["VH_SATURN_CONFIRM2_ENABLED"], "1")
            self.assertEqual(envs[0]["VH_SATURN_CONFIRM3_ENABLED"], "0")
            self.assertEqual(envs[1]["VH_SATURN_CONFIRM3_ENABLED"], "1")
            input_schedule = (
                "VH_SATURN_START_AT_FRAME",
                "VH_SATURN_CONFIRM_AT_FRAME",
                "VH_SATURN_CONFIRM_BUTTON",
                "VH_SATURN_CONFIRM_AT_FRAME2",
                "VH_SATURN_CONFIRM2_ENABLED",
                "VH_SATURN_CONFIRM_AT_FRAME3",
            )
            self.assertEqual(
                {key: envs[0][key] for key in input_schedule},
                {key: envs[1][key] for key in input_schedule},
            )
            self.assertNotEqual(envs[0]["HOME"], envs[1]["HOME"])
            self.assertNotEqual(
                envs[0]["VH_SATURN_PRIVATE_FRAMES_DIR"],
                envs[1]["VH_SATURN_PRIVATE_FRAMES_DIR"],
            )


if __name__ == "__main__":
    unittest.main()
