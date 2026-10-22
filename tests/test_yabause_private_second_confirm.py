"""Synthetic-only source tests for the Stage116 second C pulse."""
import unittest
from unittest.mock import patch

from test_yabause_private_start_sequence import _stage109_instrumented_fixture
from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_start_sequence import instrument_private_start_sequence
from tools.patch_yabause_private_confirm_pad import instrument_private_confirm_button
from tools.patch_yabause_private_long_window import instrument_private_48000_frame_window
from tools.patch_yabause_private_second_confirm import (
    instrument_full_private_second_confirm,
    instrument_private_second_confirm,
)


def _stage115_fixture():
    stage112 = instrument_private_start_sequence(_stage109_instrumented_fixture())
    stage114 = instrument_private_confirm_button(stage112)
    return instrument_private_48000_frame_window(stage114)


def _mode(source):
    text = source.decode("utf-8")
    start = text.index(MODE_START)
    end = text.index(MODE_END, start) + len(MODE_END)
    return text[start:end]


class Stage116SecondConfirmSourceTests(unittest.TestCase):
    def test_adds_optional_second_c_pulse_and_preserves_48k_runner(self):
        stage115 = _stage115_fixture()
        patched = instrument_private_second_confirm(stage115)
        mode = _mode(patched)
        self.assertEqual(mode.count("frames > 48000"), 1)
        self.assertEqual(mode.count("VH_SATURN_CONFIRM_AT_FRAME2"), 1)
        self.assertEqual(mode.count("VH_SATURN_CONFIRM2_ENABLED"), 1)
        self.assertEqual(mode.count("vh116_confirm_at2"), 6)
        self.assertEqual(mode.count("vh116_confirm2_enabled"), 4)
        self.assertIn("vh116_enable2[0] != '0'", mode)
        self.assertIn("vh116_enable2[0] != '1'", mode)
        self.assertEqual(mode.count("PerPadCPressed(vh107_pad);"), 2)
        self.assertEqual(mode.count("PerPadCReleased(vh107_pad);"), 2)
        self.assertIn("vh114_confirm_button != 'C'", mode)
        self.assertIn("n116 < (long)vh114_confirm_at + 12L", mode)
        self.assertIn("n116 > (long)frames - 8L", mode)
        self.assertIn("const unsigned char vh116_mask = 0x02U;", mode)
        self.assertEqual(patched.count(b"YabauseEmulate()"), stage115.count(b"YabauseEmulate()"))
        self.assertEqual(patched.count(b"vh101_snapshot("), stage115.count(b"vh101_snapshot("))
        self.assertEqual(patched.count(b"vh102_snapshot("), stage115.count(b"vh102_snapshot("))

    def test_rejects_duplicate_or_unpinned_second_confirm_patch(self):
        stage115 = _stage115_fixture()
        for candidate in (b"", b"int main(){return 0;}",
                          stage115.replace(b"frames > 48000", b"frames >= 48000")):
            with self.subTest(size=len(candidate)), self.assertRaises(ValueError):
                instrument_private_second_confirm(candidate)
        with self.assertRaisesRegex(ValueError, "already instrumented"):
            instrument_private_second_confirm(instrument_private_second_confirm(stage115))

    def test_full_pipeline_composes_stage115_then_second_confirm(self):
        expected = (
            b"VH_SATURN_CONFIRM_AT_FRAME VH_SATURN_CONFIRM_AT_FRAME2 "
            b"VH_SATURN_CONFIRM2_ENABLED VH_SATURN_CONFIRM_BUTTON "
            b"frames > 48000 frames.stats "
            b"video-state.txt sh2-window.txt pad-state.txt"
        )
        with (
            patch(
                "tools.patch_yabause_private_second_confirm.instrument_full_private_long_window",
                return_value=b"stage115",
            ) as stage115,
            patch(
                "tools.patch_yabause_private_second_confirm.instrument_private_second_confirm",
                return_value=expected,
            ) as stage116,
        ):
            result = instrument_full_private_second_confirm(b"pinned-upstream")
        self.assertEqual(result, expected)
        stage115.assert_called_once_with(b"pinned-upstream")
        stage116.assert_called_once_with(b"stage115")


if __name__ == "__main__":
    unittest.main()
