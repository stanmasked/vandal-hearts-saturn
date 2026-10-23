"""Synthetic-only source tests for Stage119's fifth C pulse."""
import unittest
from unittest.mock import patch

from test_yabause_private_third_confirm import _stage116_fixture
from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_third_confirm import instrument_private_third_confirm
from tools.patch_yabause_private_fourth_confirm import instrument_private_fourth_confirm
from tools.patch_yabause_private_fifth_confirm import (
    SETUP_CONFIRM5, instrument_full_private_fifth_confirm,
    instrument_private_fifth_confirm,
)


def _stage118_fixture():
    stage117 = instrument_private_third_confirm(_stage116_fixture())
    return instrument_private_fourth_confirm(stage117)


def _mode(source):
    text = source.decode("utf-8")
    start = text.index(MODE_START)
    end = text.index(MODE_END, start) + len(MODE_END)
    return text[start:end]


class Stage119FifthConfirmSourceTests(unittest.TestCase):
    def test_adds_guarded_fifth_c_and_preserves_stage118(self):
        stage118 = _stage118_fixture()
        patched = instrument_private_fifth_confirm(stage118)
        mode = _mode(patched)
        self.assertEqual(mode.count("frames > 60000"), 1)
        self.assertNotIn("frames > 48000", mode)
        self.assertEqual(mode.count("VH_SATURN_CONFIRM_AT_FRAME5"), 1)
        self.assertEqual(mode.count("VH_SATURN_CONFIRM5_ENABLED"), 1)
        self.assertEqual(mode.count("vh119_confirm_at5"), 6)
        self.assertEqual(mode.count("vh119_confirm5_enabled"), 4)
        self.assertIn("vh118_confirm_at4 < 0", mode)
        self.assertIn("vh118_confirm4_enabled != 1", mode)
        self.assertIn("n119 < (long)vh118_confirm_at4 + 12L", mode)
        self.assertIn("n119 > (long)frames - 8L", mode)
        self.assertEqual(mode.count("PerPadCPressed(vh107_pad);"), 5)
        self.assertEqual(mode.count("PerPadCReleased(vh107_pad);"), 5)
        self.assertEqual(mode.count("VH_PAD frame=%d button=%c action=PRESS"), 5)
        self.assertEqual(mode.count("VH_PAD frame=%d button=%c action=RELEASE"), 5)
        self.assertEqual(mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=0"), 5)
        self.assertEqual(mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=1"), 5)
        self.assertEqual(patched.count(b"YabauseEmulate()"), stage118.count(b"YabauseEmulate()"))
        self.assertEqual(patched.count(b"vh101_snapshot("), stage118.count(b"vh101_snapshot("))
        self.assertEqual(patched.count(b"vh102_snapshot("), stage118.count(b"vh102_snapshot("))
        self.assertIn("frame == vh119_confirm_at5", mode)
        self.assertIn("frame == vh119_confirm_at5 + 6", mode)

    def test_fifth_c_requires_enabled_fourth_c_and_bounded_schedule(self):
        for token in (
            "vh118_confirm_at4 < 0",
            "vh118_confirm4_enabled != 1",
            "n119 < (long)vh118_confirm_at4 + 12L",
            "n119 > (long)frames - 8L",
            "vh119_enable5[0] != '0'",
            "vh119_enable5[0] != '1'",
        ):
            self.assertIn(token, SETUP_CONFIRM5)

    def test_rejects_duplicate_or_unpinned_fifth_confirm_patch(self):
        stage118 = _stage118_fixture()
        with self.assertRaisesRegex(ValueError, "already instrumented"):
            instrument_private_fifth_confirm(instrument_private_fifth_confirm(stage118))
        with self.assertRaisesRegex(ValueError, "unpinned"):
            instrument_private_fifth_confirm(b"int main(){return 0;}")
        wrong_bound = stage118.replace(b"frames > 48000", b"frames >= 48000")
        with self.assertRaisesRegex(ValueError, "48,000-frame cap"):
            instrument_private_fifth_confirm(wrong_bound)

    def test_full_pipeline_composes_stage118_then_fifth_confirm(self):
        expected = (
            b"VH_SATURN_START_AT_FRAME VH_SATURN_CONFIRM_AT_FRAME "
            b"VH_SATURN_CONFIRM_AT_FRAME2 VH_SATURN_CONFIRM2_ENABLED "
            b"VH_SATURN_CONFIRM_AT_FRAME3 VH_SATURN_CONFIRM3_ENABLED "
            b"VH_SATURN_CONFIRM_AT_FRAME4 VH_SATURN_CONFIRM4_ENABLED "
            b"VH_SATURN_CONFIRM_AT_FRAME5 VH_SATURN_CONFIRM5_ENABLED "
            b"VH_SATURN_CONFIRM_BUTTON PerPadCPressed(vh107_pad); "
            b"PerPadCReleased(vh107_pad); frames > 60000 frames.stats "
            b"video-state.txt sh2-window.txt pad-state.txt"
        )
        with (
            patch(
                "tools.patch_yabause_private_fifth_confirm.instrument_full_private_fourth_confirm",
                return_value=b"stage118",
            ) as stage118,
            patch(
                "tools.patch_yabause_private_fifth_confirm.instrument_private_fifth_confirm",
                return_value=expected,
            ) as stage119,
        ):
            result = instrument_full_private_fifth_confirm(b"pinned-upstream")
        self.assertEqual(result, expected)
        stage118.assert_called_once_with(b"pinned-upstream")
        stage119.assert_called_once_with(b"stage118")


if __name__ == "__main__":
    unittest.main()
