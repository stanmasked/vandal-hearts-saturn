"""Synthetic-only source tests for the Stage117 third C dialogue pulse."""
import unittest
from unittest.mock import patch

from test_yabause_private_start_sequence import _stage109_instrumented_fixture
from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_confirm_pad import instrument_private_confirm_button
from tools.patch_yabause_private_long_window import instrument_private_48000_frame_window
from tools.patch_yabause_private_second_confirm import instrument_private_second_confirm
from tools.patch_yabause_private_start_sequence import instrument_private_start_sequence
from tools.patch_yabause_private_third_confirm import (
    CONFIRM3_PRESS,
    CONFIRM3_RELEASE,
    SETUP_CONFIRM3,
    instrument_full_private_third_confirm,
    instrument_private_third_confirm,
)


def _stage116_fixture():
    stage112 = instrument_private_start_sequence(_stage109_instrumented_fixture())
    stage114 = instrument_private_confirm_button(stage112)
    stage115 = instrument_private_48000_frame_window(stage114)
    return instrument_private_second_confirm(stage115)


def _mode(source):
    text = source.decode("utf-8")
    start = text.index(MODE_START)
    end = text.index(MODE_END, start) + len(MODE_END)
    return text[start:end]


class Stage117ThirdConfirmSourceTests(unittest.TestCase):
    def test_adds_one_guarded_third_c_and_preserves_prior_pulses(self):
        stage116 = _stage116_fixture()
        result = instrument_private_third_confirm(stage116)
        mode = _mode(result)
        self.assertEqual(mode.count("frames > 48000"), 1)
        self.assertEqual(mode.count("VH_SATURN_CONFIRM_AT_FRAME2"), 1)
        self.assertEqual(mode.count("VH_SATURN_CONFIRM2_ENABLED"), 1)
        self.assertEqual(mode.count("VH_SATURN_CONFIRM_AT_FRAME3"), 1)
        self.assertEqual(mode.count("VH_SATURN_CONFIRM3_ENABLED"), 1)
        self.assertEqual(mode.count("PerPadCPressed(vh107_pad);"), 3)
        self.assertEqual(mode.count("PerPadCReleased(vh107_pad);"), 3)
        self.assertIn("vh116_confirm2_enabled != 1", mode)
        self.assertIn("n117 < (long)vh116_confirm_at2 + 12L", mode)
        self.assertIn("n117 > (long)frames - 8L", mode)
        self.assertEqual(mode.count("YabauseEmulate()"), 1)
        self.assertLess(mode.index(CONFIRM3_PRESS), mode.index("if (YabauseEmulate() != 0)"))
        self.assertLess(mode.index(CONFIRM3_RELEASE), mode.index("if (YabauseEmulate() != 0)"))
        self.assertEqual(result.count(b"vh101_snapshot("), stage116.count(b"vh101_snapshot("))
        self.assertEqual(result.count(b"vh102_snapshot("), stage116.count(b"vh102_snapshot("))

    def test_third_pulse_uses_same_active_low_controller_api(self):
        self.assertIn("PerPadCPressed(vh107_pad);", CONFIRM3_PRESS)
        self.assertIn("PerPadCReleased(vh107_pad);", CONFIRM3_RELEASE)
        self.assertIn("VH_PADSTATE frame=%d button=%c active_low_bit=0", CONFIRM3_PRESS)
        self.assertIn("VH_PADSTATE frame=%d button=%c active_low_bit=1", CONFIRM3_RELEASE)
        self.assertIn("vh116_confirm2_enabled != 1", SETUP_CONFIRM3)

    def test_rejects_reapplication_and_missing_stage116_pulse(self):
        stage116 = _stage116_fixture()
        with self.assertRaisesRegex(ValueError, "already instrumented"):
            instrument_private_third_confirm(instrument_private_third_confirm(stage116))
        with self.assertRaisesRegex(ValueError, "unpinned"):
            instrument_private_third_confirm(b"int main(){return 0;}")
        without_second = stage116.replace(b"VH_SATURN_CONFIRM_AT_FRAME2", b"VH_SATURN_CONFIRM_AT_FRAME9")
        with self.assertRaisesRegex(ValueError, "requires Stage116"):
            instrument_private_third_confirm(without_second)

    def test_full_pipeline_composes_stage115_stage116_then_stage117(self):
        expected = (
            b"VH_SATURN_START_AT_FRAME VH_SATURN_CONFIRM_AT_FRAME "
            b"VH_SATURN_CONFIRM_AT_FRAME2 VH_SATURN_CONFIRM2_ENABLED "
            b"VH_SATURN_CONFIRM_AT_FRAME3 VH_SATURN_CONFIRM3_ENABLED "
            b"PerPadCPressed(vh107_pad); PerPadCReleased(vh107_pad); "
            b"frames > 48000 frames.stats video-state.txt sh2-window.txt pad-state.txt"
        )
        with (
            patch(
                "tools.patch_yabause_private_third_confirm.instrument_full_private_long_window",
                return_value=b"stage115",
            ) as stage115,
            patch(
                "tools.patch_yabause_private_third_confirm.instrument_private_second_confirm",
                return_value=b"stage116",
            ) as stage116,
            patch(
                "tools.patch_yabause_private_third_confirm.instrument_private_third_confirm",
                return_value=expected,
            ) as stage117,
        ):
            result = instrument_full_private_third_confirm(b"pinned-upstream")
        self.assertEqual(result, expected)
        stage115.assert_called_once_with(b"pinned-upstream")
        stage116.assert_called_once_with(b"stage115")
        stage117.assert_called_once_with(b"stage116")


if __name__ == "__main__":
    unittest.main()
