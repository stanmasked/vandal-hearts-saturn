"""Synthetic-only tests for Stage119's private fifth-C paired audit."""
from pathlib import Path
import tempfile
import unittest

from test_saturn_private_original_start_triple import _png, _write
from test_saturn_private_prologue_continue_third_c import _populate
from tools.saturn_private_first_battle_window import FRAME_COUNT
from tools.saturn_private_prologue_continue_fourth_c import QUAD_C_EVENTS, QUAD_C_STATE
from tools.saturn_private_prologue_continue_fifth_c import (
    CONFIRM5_PRESS, CONFIRM5_RELEASE, FIFTH_C_EVENTS, FIFTH_C_STATE,
    audit_private_prologue_continue_fifth_c,
)


class Stage119PrivateDialogueAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o700)
        self.fourth_c = self.root / "fourth-c"
        self.fifth_c = self.root / "fifth-c"
        for folder in (self.fourth_c, self.fifth_c):
            folder.mkdir(mode=0o700)
            folder.chmod(0o700)
            _populate(folder, True)
        _write(self.fourth_c, "pad-events.txt", QUAD_C_EVENTS)
        _write(self.fourth_c, "pad-state.txt", QUAD_C_STATE)
        _write(self.fifth_c, "pad-events.txt", FIFTH_C_EVENTS)
        _write(self.fifth_c, "pad-state.txt", FIFTH_C_STATE)
        # The fourth-C baseline and fifth-C intervention match until frame 46000.
        for frame in range(CONFIRM5_PRESS + 120, FRAME_COUNT + 1, 120):
            _write(self.fifth_c, f"frame-{frame}.png", _png((180, 190, 200)))
        _write(self.fifth_c, "post.png", _png((180, 190, 200)))

    def test_accepts_fifth_c_effect_with_valid_48k_pair(self):
        report = audit_private_prologue_continue_fifth_c(self.fourth_c, self.fifth_c)
        self.assertEqual(report["frames_per_process"], 48000)
        self.assertEqual(report["fifth_C_press_frame"], CONFIRM5_PRESS)
        self.assertEqual(report["fifth_C_release_frame"], CONFIRM5_RELEASE)
        self.assertEqual(report["pre_fifth_checkpoint_equal_count"], 383)
        self.assertEqual(report["pre_fifth_checkpoint_total"], 383)
        self.assertTrue(report["all_pre_fifth_C_checkpoints_match"])
        self.assertEqual(report["first_post_fifth_C_framebuffer_divergence_by_47200"], 46120)
        self.assertTrue(report["frame_48000_differs"])
        self.assertFalse(report["first_battle_or_player_control_verified"])
        self.assertFalse(report["original_media_or_frame_hashes_exported"])

    def test_rejects_divergence_before_fifth_c(self):
        _write(self.fifth_c, "frame-45960.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "before fifth C confirm"):
            audit_private_prologue_continue_fifth_c(self.fourth_c, self.fifth_c)

    def test_rejects_no_fifth_c_effect_by_47200(self):
        for frame in range(CONFIRM5_PRESS + 120, FRAME_COUNT + 1, 120):
            _write(
                self.fifth_c, f"frame-{frame}.png",
                (self.fourth_c / f"frame-{frame}.png").read_bytes(),
            )
        _write(self.fifth_c, "post.png", (self.fourth_c / "post.png").read_bytes())
        with self.assertRaisesRegex(ValueError, "no framebuffer effect by frame 47200"):
            audit_private_prologue_continue_fifth_c(self.fourth_c, self.fifth_c)

    def test_rejects_wrong_fifth_c_active_low_receipt(self):
        _write(
            self.fifth_c, "pad-state.txt",
            b"VH_PADSTATE frame=46000 button=C active_low_bit=1\n",
        )
        with self.assertRaisesRegex(ValueError, "fifth-C active-low receipt"):
            audit_private_prologue_continue_fifth_c(self.fourth_c, self.fifth_c)

    def test_rejects_missing_last_checkpoint(self):
        (self.fifth_c / "frame-48000.png").unlink()
        with self.assertRaisesRegex(ValueError, "file set mismatch"):
            audit_private_prologue_continue_fifth_c(self.fourth_c, self.fifth_c)

    def test_rejects_unequal_output_path_shape(self):
        other = self.root / "fifth-c-long"
        other.mkdir(mode=0o700)
        other.chmod(0o700)
        with self.assertRaisesRegex(ValueError, "equal length"):
            audit_private_prologue_continue_fifth_c(self.fourth_c, other)


if __name__ == "__main__":
    unittest.main()
