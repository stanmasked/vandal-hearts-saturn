"""Synthetic-only tests for Stage118's private fourth-C paired audit."""
from pathlib import Path
import tempfile
import unittest

from test_saturn_private_original_start_triple import _png, _write
from test_saturn_private_prologue_continue_third_c import _populate
from tools.saturn_private_first_battle_window import FRAME_COUNT
from tools.saturn_private_prologue_continue_fourth_c import (
    CONFIRM4_PRESS, CONFIRM4_RELEASE, QUAD_C_EVENTS, QUAD_C_STATE,
    TRIPLE_C_EVENTS, TRIPLE_C_STATE, audit_private_prologue_continue_fourth_c,
)


class Stage118PrivateDialogueAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o700)
        self.triple_c = self.root / "triple-c"
        self.fourth_c = self.root / "fourth-c"
        for folder in (self.triple_c, self.fourth_c):
            folder.mkdir(mode=0o700)
            folder.chmod(0o700)
            _populate(folder, True)
        _write(self.triple_c, "pad-events.txt", TRIPLE_C_EVENTS)
        _write(self.triple_c, "pad-state.txt", TRIPLE_C_STATE)
        _write(self.fourth_c, "pad-events.txt", QUAD_C_EVENTS)
        _write(self.fourth_c, "pad-state.txt", QUAD_C_STATE)
        # Identical triple-C baseline until the fourth C at frame 42000.
        for frame in range(CONFIRM4_PRESS + 120, FRAME_COUNT + 1, 120):
            _write(self.fourth_c, f"frame-{frame}.png", _png((180, 190, 200)))
        _write(self.fourth_c, "post.png", _png((180, 190, 200)))

    def test_accepts_fourth_c_effect_with_valid_48k_pair(self):
        report = audit_private_prologue_continue_fourth_c(self.triple_c, self.fourth_c)
        self.assertEqual(report["frames_per_process"], 48000)
        self.assertEqual(report["fourth_C_press_frame"], CONFIRM4_PRESS)
        self.assertEqual(report["fourth_C_release_frame"], CONFIRM4_RELEASE)
        self.assertEqual(report["pre_fourth_checkpoint_equal_count"], 349)
        self.assertEqual(report["pre_fourth_checkpoint_total"], 349)
        self.assertTrue(report["all_pre_fourth_C_checkpoints_match"])
        self.assertEqual(report["first_post_fourth_C_framebuffer_divergence_by_43200"], 42120)
        self.assertTrue(report["frame_48000_differs"])
        self.assertFalse(report["first_battle_or_player_control_verified"])
        self.assertFalse(report["original_media_or_frame_hashes_exported"])

    def test_rejects_divergence_before_fourth_c(self):
        _write(self.fourth_c, "frame-41880.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "before fourth C confirm"):
            audit_private_prologue_continue_fourth_c(self.triple_c, self.fourth_c)

    def test_rejects_no_fourth_c_effect_by_43200(self):
        for frame in range(CONFIRM4_PRESS + 120, FRAME_COUNT + 1, 120):
            _write(
                self.fourth_c, f"frame-{frame}.png",
                (self.triple_c / f"frame-{frame}.png").read_bytes(),
            )
        _write(self.fourth_c, "post.png", (self.triple_c / "post.png").read_bytes())
        with self.assertRaisesRegex(ValueError, "no framebuffer effect by frame 43200"):
            audit_private_prologue_continue_fourth_c(self.triple_c, self.fourth_c)

    def test_rejects_wrong_fourth_c_active_low_receipt(self):
        _write(
            self.fourth_c, "pad-state.txt",
            b"VH_PADSTATE frame=42000 button=C active_low_bit=1\n",
        )
        with self.assertRaisesRegex(ValueError, "fourth-C active-low receipt"):
            audit_private_prologue_continue_fourth_c(self.triple_c, self.fourth_c)

    def test_rejects_missing_last_checkpoint(self):
        (self.fourth_c / "frame-48000.png").unlink()
        with self.assertRaisesRegex(ValueError, "file set mismatch"):
            audit_private_prologue_continue_fourth_c(self.triple_c, self.fourth_c)

    def test_rejects_unequal_output_path_shape(self):
        other = self.root / "fourth-c-long"
        other.mkdir(mode=0o700)
        other.chmod(0o700)
        with self.assertRaisesRegex(ValueError, "equal length"):
            audit_private_prologue_continue_fourth_c(self.triple_c, other)


if __name__ == "__main__":
    unittest.main()
