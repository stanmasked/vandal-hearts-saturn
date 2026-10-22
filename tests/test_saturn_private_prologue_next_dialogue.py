"""Synthetic-only tests for Stage117's private third-C paired audit."""
from pathlib import Path
import unittest

from test_saturn_private_original_start_triple import _png, _write
from test_saturn_private_prologue_continue import _populate
from tools.saturn_private_first_battle_window import FRAME_COUNT
from tools.saturn_private_prologue_next_dialogue import (
    CONFIRM3_PRESS, CONFIRM3_RELEASE, TRIPLE_C_EVENTS, TRIPLE_C_STATE,
    audit_private_prologue_next_dialogue,
)


def _add_triple_c_receipt(folder):
    _write(folder, "pad-events.txt", TRIPLE_C_EVENTS)
    _write(folder, "pad-state.txt", TRIPLE_C_STATE)


class Stage117PrivateNextDialogueAuditTests(unittest.TestCase):
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
            _populate(folder, True)
        _add_triple_c_receipt(self.triple_c)
        for frame in range(CONFIRM3_PRESS + 120, FRAME_COUNT + 1, 120):
            _write(self.triple_c, f"frame-{frame}.png", _png((160, 170, 180)))
        _write(self.triple_c, "post.png", _png((160, 170, 180)))

    def test_accepts_third_c_effect_with_valid_48k_pair(self):
        report = audit_private_prologue_next_dialogue(self.double_c, self.triple_c)
        self.assertEqual(report["frames_per_process"], 48000)
        self.assertEqual(report["third_C_press_frame"], CONFIRM3_PRESS)
        self.assertEqual(report["third_C_release_frame"], CONFIRM3_RELEASE)
        self.assertEqual(report["pre_third_checkpoint_equal_count"], 349)
        self.assertEqual(report["pre_third_checkpoint_total"], 349)
        self.assertTrue(report["all_pre_third_C_checkpoints_match"])
        self.assertEqual(report["first_post_third_C_framebuffer_divergence"], 42120)
        self.assertTrue(report["frame_48000_differs_after_third_C"])
        self.assertFalse(report["first_battle_or_player_control_verified"])
        self.assertFalse(report["original_media_or_frame_hashes_exported"])

    def test_rejects_divergence_before_third_c(self):
        _write(self.triple_c, "frame-41880.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "before third C confirm"):
            audit_private_prologue_next_dialogue(self.double_c, self.triple_c)

    def test_rejects_no_observed_third_c_effect(self):
        for frame in range(CONFIRM3_PRESS + 120, FRAME_COUNT + 1, 120):
            _write(
                self.triple_c, f"frame-{frame}.png",
                (self.double_c / f"frame-{frame}.png").read_bytes(),
            )
        _write(self.triple_c, "post.png", (self.double_c / "post.png").read_bytes())
        with self.assertRaisesRegex(ValueError, "no framebuffer effect"):
            audit_private_prologue_next_dialogue(self.double_c, self.triple_c)

    def test_rejects_wrong_third_c_receipt(self):
        _write(
            self.triple_c, "pad-state.txt",
            b"VH_PADSTATE frame=42000 button=C active_low_bit=1\n",
        )
        with self.assertRaisesRegex(ValueError, "third-C active-low receipt"):
            audit_private_prologue_next_dialogue(self.double_c, self.triple_c)

    def test_rejects_missing_last_checkpoint(self):
        (self.triple_c / "frame-48000.png").unlink()
        with self.assertRaisesRegex(ValueError, "file set mismatch"):
            audit_private_prologue_next_dialogue(self.double_c, self.triple_c)


if __name__ == "__main__":
    unittest.main()
