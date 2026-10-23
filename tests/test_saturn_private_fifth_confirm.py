"""Invented-only Stage119 paired fifth-C auditor regression tests."""
from pathlib import Path
import tempfile
import unittest

from test_saturn_private_original_start_triple import _png, _write
from test_saturn_private_prologue_continue_third_c import _populate
from tools.saturn_private_fifth_confirm import (
    FIVE_C_EVENTS, FIVE_C_STATE, QUAD_C_EVENTS, QUAD_C_STATE,
    CONFIRM5_PRESS, audit_private_fifth_confirm,
)


class Stage119PrivateFifthConfirmAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o700)
        self.fourth = self.root / "fourth-c"
        self.fifth = self.root / "fifth-cc"
        for folder in (self.fourth, self.fifth):
            folder.mkdir(mode=0o700)
            folder.chmod(0o700)
            _populate(folder, True)
        _write(self.fourth, "pad-events.txt", QUAD_C_EVENTS)
        _write(self.fourth, "pad-state.txt", QUAD_C_STATE)
        _write(self.fifth, "pad-events.txt", FIVE_C_EVENTS)
        _write(self.fifth, "pad-state.txt", FIVE_C_STATE)
        for frame in range(CONFIRM5_PRESS + 120, 48000 + 1, 120):
            _write(self.fifth, f"frame-{frame}.png", _png((122, 133, 144)))
        _write(self.fifth, "post.png", _png((122, 133, 144)))

    def test_accepts_fifth_c_transition(self):
        result = audit_private_fifth_confirm(self.fourth, self.fifth)
        self.assertEqual(result["pre_fifth_checkpoint_equal_count"], 379)
        self.assertEqual(result["fifth_C_press_frame"], 45600)
        self.assertEqual(result["first_post_fifth_framebuffer_divergence_by_46800"], 45720)
        self.assertEqual(result["checkpoint_png_count_per_process"], 400)
        self.assertTrue(result["all_pre_fifth_C_checkpoints_match"])
        self.assertFalse(result["first_controllable_tactical_battle_verified"])

    def test_rejects_early_divergence(self):
        _write(self.fifth, "frame-45480.png", _png((9, 9, 9)))
        with self.assertRaisesRegex(ValueError, "before fifth C"):
            audit_private_fifth_confirm(self.fourth, self.fifth)

    def test_rejects_no_effect_after_fifth_c(self):
        for frame in range(CONFIRM5_PRESS + 120, 48000 + 1, 120):
            _write(self.fifth, f"frame-{frame}.png", (self.fourth / f"frame-{frame}.png").read_bytes())
        _write(self.fifth, "post.png", (self.fourth / "post.png").read_bytes())
        with self.assertRaisesRegex(ValueError, "no framebuffer effect"):
            audit_private_fifth_confirm(self.fourth, self.fifth)

    def test_rejects_wrong_active_low_state(self):
        _write(self.fifth, "pad-state.txt", b"invalid\n")
        with self.assertRaisesRegex(ValueError, "active-low"):
            audit_private_fifth_confirm(self.fourth, self.fifth)

    def test_rejects_unequal_output_paths(self):
        other = self.root / "too-long-fifth"
        other.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError, "equal-length sibling"):
            audit_private_fifth_confirm(self.fourth, other)


if __name__ == "__main__":
    unittest.main()
