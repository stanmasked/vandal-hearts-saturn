"""Synthetic-only tests for Stage116's private second-C dialogue audit."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_saturn_private_original_start_triple import _png, _write
from tools.saturn_private_first_battle_window import FRAME_COUNT
from tools.saturn_private_prologue_continue import (
    CONFIRM_PRESS, CONFIRM_RELEASE, CONFIRM2_PRESS, CONFIRM2_RELEASE,
    SINGLE_C_EVENTS, SINGLE_C_STATE, DOUBLE_C_EVENTS, DOUBLE_C_STATE,
    _run_one, audit_private_prologue_continue,
)

SAMPLES = [0] + list(range(120, FRAME_COUNT + 1, 120)) + [FRAME_COUNT]


def _populate(folder, double_c):
    _write(folder, "pad-events.txt", DOUBLE_C_EVENTS if double_c else SINGLE_C_EVENTS)
    _write(folder, "pad-state.txt", DOUBLE_C_STATE if double_c else SINGLE_C_STATE)
    _write(folder, "fad.vhcdlog", b"VHCD_FAD 150\n")
    _write(folder, "pre.png", _png((25, 35, 45)))
    _write(folder, "post.png", _png((130, 140, 150) if double_c else (90, 100, 110)))
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
        elif frame < CONFIRM2_PRESS + 120:
            color = (90, 100, 110)
        elif double_c:
            color = (130, 140, 150)
        else:
            color = (90, 100, 110)
        _write(folder, f"frame-{frame}.png", _png(color))


class Stage116PrivateDialogueAuditTests(unittest.TestCase):
    def test_paired_runs_receive_same_schedule_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            root.chmod(0o700)
            single = root / "single"
            double = root / "double"
            single.mkdir(mode=0o700)
            double.mkdir(mode=0o700)
            captured = []

            class FakeProcess:
                pid = 999999

                def wait(self, timeout):
                    return 0

            def fake_popen(args, **kwargs):
                captured.append(kwargs["env"])
                return FakeProcess()

            with patch(
                "tools.saturn_private_prologue_continue.subprocess.Popen",
                side_effect=fake_popen,
            ):
                _run_one(Path("/bin/true"), root / "unused.cue", single,
                         second_c=False, seconds=5)
                _run_one(Path("/bin/true"), root / "unused.cue", double,
                         second_c=True, seconds=5)

            self.assertEqual(len(captured), 2)
            self.assertEqual(set(captured[0]), set(captured[1]))
            self.assertEqual(captured[0]["VH_SATURN_CONFIRM_AT_FRAME2"], "31200")
            self.assertEqual(captured[1]["VH_SATURN_CONFIRM_AT_FRAME2"], "31200")
            self.assertEqual(captured[0]["VH_SATURN_CONFIRM2_ENABLED"], "0")
            self.assertEqual(captured[1]["VH_SATURN_CONFIRM2_ENABLED"], "1")
            for key in (
                "VH_SATURN_START_AT_FRAME",
                "VH_SATURN_CONFIRM_AT_FRAME",
                "VH_SATURN_CONFIRM_BUTTON",
            ):
                self.assertEqual(captured[0][key], captured[1][key])

    def setUp(self):
        import tempfile
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o700)
        self.single_c = self.root / "single-c"
        self.double_c = self.root / "double-c"
        for folder in (self.single_c, self.double_c):
            folder.mkdir(mode=0o700)
            folder.chmod(0o700)
        _populate(self.single_c, False)
        _populate(self.double_c, True)

    def test_accepts_second_c_effect_with_valid_48k_pair(self):
        report = audit_private_prologue_continue(self.single_c, self.double_c)
        self.assertEqual(report["frames_per_process"], 48000)
        self.assertEqual(report["second_C_press_frame"], CONFIRM2_PRESS)
        self.assertEqual(report["second_C_release_frame"], CONFIRM2_RELEASE)
        self.assertEqual(report["pre_second_checkpoint_equal_count"], 259)
        self.assertEqual(report["pre_second_checkpoint_total"], 259)
        self.assertEqual(report["stable_pre_second_checkpoint_total"], 256)
        self.assertEqual(report["known_intro_fmv_checkpoint_differences"], [])
        self.assertTrue(report["all_stable_pre_second_C_checkpoints_match"])
        self.assertEqual(report["first_post_second_C_framebuffer_divergence_by_36000"], 31320)
        self.assertEqual(report["first_post_second_C_framebuffer_divergence_through_48000"], 31320)
        self.assertTrue(report["frame_32400_differs_after_second_C"])
        self.assertFalse(report["first_battle_or_player_control_verified"])
        self.assertFalse(report["original_media_or_frame_hashes_exported"])

    def test_rejects_unequal_output_path_shape(self):
        with self.assertRaisesRegex(ValueError, "equal length"):
            audit_private_prologue_continue(
                self.root / "short", self.root / "longer-control"
            )

    def test_rejects_divergence_before_first_c(self):
        _write(self.double_c, "frame-12120.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "before first C confirm"):
            audit_private_prologue_continue(self.single_c, self.double_c)

    def test_rejects_pre_second_c_divergence(self):
        # The only intended intervention after the first C is at frame 31200.
        # Any earlier A/B difference invalidates attribution to the second C.
        _write(self.double_c, "frame-30000.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "diverged before second C confirm"):
            audit_private_prologue_continue(self.single_c, self.double_c)

    def test_allows_only_the_three_reviewed_intro_fmv_checkpoints(self):
        for frame in (6240, 9720, 9960):
            _write(self.double_c, f"frame-{frame}.png", _png((1, 2, 3)))
        report = audit_private_prologue_continue(self.single_c, self.double_c)
        self.assertEqual(
            report["known_intro_fmv_checkpoint_differences"],
            [6240, 9720, 9960],
        )
        self.assertEqual(report["pre_second_checkpoint_equal_count"], 256)
        self.assertEqual(report["stable_pre_second_checkpoint_total"], 256)
        self.assertTrue(report["all_stable_pre_second_C_checkpoints_match"])

    def test_rejects_unreviewed_pre_start_difference(self):
        _write(self.double_c, "frame-6000.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "diverged before first START"):
            audit_private_prologue_continue(self.single_c, self.double_c)

    def test_rejects_no_post_second_c_effect(self):
        for frame in range(CONFIRM2_PRESS + 120, 36000 + 1, 120):
            _write(
                self.double_c,
                f"frame-{frame}.png",
                (self.single_c / f"frame-{frame}.png").read_bytes(),
            )
        with self.assertRaisesRegex(ValueError, "no framebuffer effect"):
            audit_private_prologue_continue(self.single_c, self.double_c)

    def test_rejects_wrong_second_c_active_low_receipt(self):
        _write(self.double_c, "pad-state.txt", b"VH_PADSTATE frame=31200 button=C active_low_bit=1\n")
        with self.assertRaisesRegex(ValueError, "second-C active-low receipt"):
            audit_private_prologue_continue(self.single_c, self.double_c)

    def test_rejects_missing_last_checkpoint(self):
        (self.double_c / "frame-48000.png").unlink()
        with self.assertRaisesRegex(ValueError, "file set mismatch"):
            audit_private_prologue_continue(self.single_c, self.double_c)


if __name__ == "__main__":
    unittest.main()
