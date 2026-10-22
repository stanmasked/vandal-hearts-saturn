"""Synthetic-only tests for the Stage117 third-dialogue paired auditor."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_saturn_private_original_start_triple import _png, _write
from test_saturn_private_prologue_continue import _populate
from tools.saturn_private_third_dialogue import (
    CONFIRM2_PRESS, CONFIRM3_PRESS, CONFIRM3_RELEASE, FRAME_COUNT,
    DOUBLE_C_EVENTS, DOUBLE_C_STATE, TRIPLE_C_EVENTS, TRIPLE_C_STATE,
    _run_one, audit_private_third_dialogue,
)


def _populate_stage117(folder, triple):
    _populate(folder, True)
    if triple:
        _write(folder, "pad-events.txt", TRIPLE_C_EVENTS)
        _write(folder, "pad-state.txt", TRIPLE_C_STATE)
        for frame in range(CONFIRM3_PRESS + 120, FRAME_COUNT + 1, 120):
            _write(folder, f"frame-{frame}.png", _png((110, 120, 130)))
        _write(folder, "post.png", _png((110, 120, 130)))


class Stage117PrivateThirdDialogueTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o700)
        self.double_c = self.root / "double-c"
        self.triple_c = self.root / "triple-c"
        for folder in (self.double_c, self.triple_c):
            folder.mkdir(mode=0o700)
            folder.chmod(0o700)
        _populate_stage117(self.double_c, False)
        _populate_stage117(self.triple_c, True)

    def test_accepts_third_c_effect_after_identical_stable_prefix(self):
        report = audit_private_third_dialogue(self.double_c, self.triple_c)
        self.assertEqual(report["frames_per_process"], 48000)
        self.assertEqual(report["second_C_press_frame"], CONFIRM2_PRESS)
        self.assertEqual(report["third_C_press_frame"], CONFIRM3_PRESS)
        self.assertEqual(report["third_C_release_frame"], CONFIRM3_RELEASE)
        self.assertEqual(report["stable_pre_third_checkpoint_equal_count"], 324)
        self.assertEqual(report["stable_pre_third_checkpoint_total"], 321)
        self.assertEqual(report["first_post_third_C_framebuffer_divergence_by_45000"], 39120)
        self.assertTrue(report["frame_42000_differs_after_third_C"])
        self.assertFalse(report["first_battle_or_player_control_verified"])
        self.assertFalse(report["original_media_or_frame_hashes_exported"])

    def test_allows_only_reviewed_intro_fmv_differences(self):
        for frame in (6240, 9720, 9960):
            _write(self.triple_c, f"frame-{frame}.png", _png((1, 2, 3)))
        report = audit_private_third_dialogue(self.double_c, self.triple_c)
        self.assertEqual(report["known_intro_fmv_checkpoint_differences"], [6240, 9720, 9960])
        self.assertEqual(report["stable_pre_third_checkpoint_equal_count"], 321)

    def test_rejects_unreviewed_divergence_before_third_c(self):
        _write(self.triple_c, "frame-30000.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "diverged before third C confirm"):
            audit_private_third_dialogue(self.double_c, self.triple_c)

    def test_rejects_no_post_third_c_effect(self):
        for frame in range(CONFIRM3_PRESS + 120, 45000 + 1, 120):
            _write(
                self.triple_c,
                f"frame-{frame}.png",
                (self.double_c / f"frame-{frame}.png").read_bytes(),
            )
        with self.assertRaisesRegex(ValueError, "no framebuffer effect by frame 45000"):
            audit_private_third_dialogue(self.double_c, self.triple_c)

    def test_rejects_wrong_third_c_active_low_receipt(self):
        _write(self.triple_c, "pad-state.txt", b"VH_PADSTATE frame=39000 button=C active_low_bit=1\n")
        with self.assertRaisesRegex(ValueError, "third-C active-low receipt"):
            audit_private_third_dialogue(self.double_c, self.triple_c)

    def test_both_runs_use_identical_schedule_except_third_c_enable_bit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            root.chmod(0o700)
            double_c = root / "double-c"
            triple_c = root / "triple-c"
            double_c.mkdir(mode=0o700)
            triple_c.mkdir(mode=0o700)
            captured = []

            class FakeProcess:
                pid = 999999
                def wait(self, timeout):
                    return 0

            def fake_popen(args, **kwargs):
                captured.append(kwargs["env"])
                return FakeProcess()

            with patch(
                "tools.saturn_private_third_dialogue.subprocess.Popen",
                side_effect=fake_popen,
            ):
                _run_one(Path("/bin/true"), root / "unused.cue", double_c,
                         third_c=False, seconds=5)
                _run_one(Path("/bin/true"), root / "unused.cue", triple_c,
                         third_c=True, seconds=5)
            self.assertEqual(set(captured[0]), set(captured[1]))
            for key in (
                "VH_SATURN_START_AT_FRAME",
                "VH_SATURN_CONFIRM_AT_FRAME",
                "VH_SATURN_CONFIRM_BUTTON",
                "VH_SATURN_CONFIRM_AT_FRAME2",
                "VH_SATURN_CONFIRM2_ENABLED",
                "VH_SATURN_CONFIRM_AT_FRAME3",
            ):
                self.assertEqual(captured[0][key], captured[1][key])
            self.assertEqual(captured[0]["VH_SATURN_CONFIRM2_ENABLED"], "1")
            self.assertEqual(captured[0]["VH_SATURN_CONFIRM_AT_FRAME3"], "39000")
            self.assertEqual(captured[0]["VH_SATURN_CONFIRM3_ENABLED"], "0")
            self.assertEqual(captured[1]["VH_SATURN_CONFIRM3_ENABLED"], "1")


if __name__ == "__main__":
    unittest.main()
