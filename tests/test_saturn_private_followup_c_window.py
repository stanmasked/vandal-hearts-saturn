"""Synthetic-only Stage116 tests for follow-up C input and paired auditing."""
from pathlib import Path
import tempfile
import unittest

from test_saturn_private_first_battle_window import _populate
from test_saturn_private_original_start_triple import _png, _write
from tools.saturn_private_first_battle_window import (
    CONFIRM_EVENTS, CONFIRM_STATE, FRAME_COUNT,
)
from tools.saturn_private_followup_c_window import (
    _followup_receipts,
    audit_private_followup_c_window,
)


def _add_followup_receipt(folder, frame=30000):
    events, state = _followup_receipts(frame)
    _write(folder, "pad-events.txt", events)
    _write(folder, "pad-state.txt", state)


class Stage116PrivateFollowupAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o700)
        self.initial_c = self.root / "initial-c-only"
        self.followup_c = self.root / "followup-c"
        for folder in (self.initial_c, self.followup_c):
            folder.mkdir(mode=0o700)
            folder.chmod(0o700)
            _populate(folder, True)
        _add_followup_receipt(self.followup_c)
        for frame in range(30120, FRAME_COUNT + 1, 120):
            _write(self.followup_c, f"frame-{frame}.png", _png((110, 120, 130)))
        _write(self.followup_c, "post.png", _png((110, 120, 130)))

    def test_accepts_identical_prefix_and_followup_divergence(self):
        report = audit_private_followup_c_window(
            self.initial_c, self.followup_c, 30000
        )
        self.assertEqual(report["frames_per_process"], 48000)
        self.assertEqual(report["checkpoint_png_count_per_process"], 400)
        self.assertEqual(report["followup_c_frame"], 30000)
        self.assertEqual(report["followup_c_release_frame"], 30006)
        self.assertEqual(report["runs_identical_through_frame"], 29880)
        self.assertEqual(report["first_followup_c_divergence_frame"], 30120)
        self.assertTrue(report["followup_input_effect_verified_numerically"])
        self.assertFalse(report["first_battle_or_player_control_verified"])
        self.assertFalse(report["original_media_or_frame_hashes_exported"])

    def test_rejects_divergence_before_followup_input(self):
        _write(self.followup_c, "frame-29880.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "before the follow-up C pulse"):
            audit_private_followup_c_window(
                self.initial_c, self.followup_c, 30000
            )

    def test_rejects_no_observed_followup_effect(self):
        for frame in range(30120, FRAME_COUNT + 1, 120):
            _write(
                self.followup_c,
                f"frame-{frame}.png",
                (self.initial_c / f"frame-{frame}.png").read_bytes(),
            )
        _write(
            self.followup_c, "post.png",
            (self.initial_c / "post.png").read_bytes(),
        )
        with self.assertRaisesRegex(ValueError, "no framebuffer divergence"):
            audit_private_followup_c_window(
                self.initial_c, self.followup_c, 30000
            )

    def test_rejects_wrong_followup_receipt(self):
        _write(
            self.followup_c, "pad-state.txt",
            b"VH_PADSTATE frame=30000 button=C active_low_bit=1\n",
        )
        with self.assertRaisesRegex(ValueError, "active-low receipt mismatch"):
            audit_private_followup_c_window(
                self.initial_c, self.followup_c, 30000
            )

    def test_rejects_out_of_bounds_followup_frame(self):
        for frame in (12246, 12251, FRAME_COUNT - 7, True):
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                _followup_receipts(frame)


if __name__ == "__main__":
    unittest.main()
