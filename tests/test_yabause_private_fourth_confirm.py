"""Synthetic-only source tests for Stage118's fourth C pulse."""
import unittest
from unittest.mock import patch

from test_yabause_private_third_confirm import _stage116_fixture
from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_third_confirm import instrument_private_third_confirm
from tools.patch_yabause_private_fourth_confirm import (
    SETUP_CONFIRM4,
    instrument_full_private_fourth_confirm, instrument_private_fourth_confirm,
)


def _stage117_fixture():
    return instrument_private_third_confirm(_stage116_fixture())


def _mode(source):
    text = source.decode("utf-8")
    start = text.index(MODE_START)
    end = text.index(MODE_END, start) + len(MODE_END)
    return text[start:end]


class Stage118FourthConfirmSourceTests(unittest.TestCase):
    def test_adds_guarded_fourth_c_and_preserves_stage117(self):
        stage117 = _stage117_fixture()
        patched = instrument_private_fourth_confirm(stage117)
        mode = _mode(patched)
        self.assertEqual(mode.count("frames > 48000"), 1)
        self.assertEqual(mode.count("VH_SATURN_CONFIRM_AT_FRAME4"), 1)
        self.assertEqual(mode.count("VH_SATURN_CONFIRM4_ENABLED"), 1)
        self.assertEqual(mode.count("vh118_confirm_at4"), 6)
        self.assertEqual(mode.count("vh118_confirm4_enabled"), 4)
        self.assertIn("vh117_confirm_at3 < 0", mode)
        self.assertIn("vh117_confirm3_enabled != 1", mode)
        self.assertIn("n118 < (long)vh117_confirm_at3 + 12L", mode)
        self.assertIn("n118 > (long)frames - 8L", mode)
        self.assertEqual(mode.count("PerPadCPressed(vh107_pad);"), 4)
        self.assertEqual(mode.count("PerPadCReleased(vh107_pad);"), 4)
        self.assertEqual(mode.count("VH_PAD frame=%d button=%c action=PRESS"), 4)
        self.assertEqual(mode.count("VH_PAD frame=%d button=%c action=RELEASE"), 4)
        self.assertEqual(mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=0"), 4)
        self.assertEqual(mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=1"), 4)
        self.assertEqual(patched.count(b"YabauseEmulate()"), stage117.count(b"YabauseEmulate()"))
        self.assertEqual(patched.count(b"vh101_snapshot("), stage117.count(b"vh101_snapshot("))
        self.assertEqual(patched.count(b"vh102_snapshot("), stage117.count(b"vh102_snapshot("))
        self.assertIn("frame == vh118_confirm_at4", mode)
        self.assertIn("frame == vh118_confirm_at4 + 6", mode)

    def test_fourth_c_requires_enabled_third_c_and_bounded_schedule(self):
        for token in (
            "vh117_confirm_at3 < 0",
            "vh117_confirm3_enabled != 1",
            "n118 < (long)vh117_confirm_at3 + 12L",
            "n118 > (long)frames - 8L",
            "vh118_enable4[0] != '0'",
            "vh118_enable4[0] != '1'",
        ):
            self.assertIn(token, SETUP_CONFIRM4)

    def test_rejects_duplicate_or_unpinned_fourth_confirm_patch(self):
        stage117 = _stage117_fixture()
        with self.assertRaisesRegex(ValueError, "already instrumented"):
            instrument_private_fourth_confirm(instrument_private_fourth_confirm(stage117))
        with self.assertRaisesRegex(ValueError, "unpinned"):
            instrument_private_fourth_confirm(b"int main(){return 0;}")
        unbounded = stage117.replace(b"frames > 48000", b"frames >= 48000")
        with self.assertRaisesRegex(ValueError, "48,000-frame cap"):
            instrument_private_fourth_confirm(unbounded)

    def test_full_pipeline_composes_stage117_then_fourth_confirm(self):
        expected = (
            b"VH_SATURN_START_AT_FRAME VH_SATURN_CONFIRM_AT_FRAME "
            b"VH_SATURN_CONFIRM_AT_FRAME2 VH_SATURN_CONFIRM2_ENABLED "
            b"VH_SATURN_CONFIRM_AT_FRAME3 VH_SATURN_CONFIRM3_ENABLED "
            b"VH_SATURN_CONFIRM_AT_FRAME4 VH_SATURN_CONFIRM4_ENABLED "
            b"VH_SATURN_CONFIRM_BUTTON PerPadCPressed(vh107_pad); "
            b"PerPadCReleased(vh107_pad); frames > 48000 frames.stats "
            b"video-state.txt sh2-window.txt pad-state.txt"
        )
        with (
            patch(
                "tools.patch_yabause_private_fourth_confirm.instrument_full_private_third_confirm",
                return_value=b"stage117",
            ) as stage117,
            patch(
                "tools.patch_yabause_private_fourth_confirm.instrument_private_fourth_confirm",
                return_value=expected,
            ) as stage118,
        ):
            result = instrument_full_private_fourth_confirm(b"pinned-upstream")
        self.assertEqual(result, expected)
        stage117.assert_called_once_with(b"pinned-upstream")
        stage118.assert_called_once_with(b"stage117")


if __name__ == "__main__":
    unittest.main()
