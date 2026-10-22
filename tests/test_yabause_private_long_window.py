"""Synthetic-only tests for the Stage115 48,000-frame source patch."""
import unittest
from unittest.mock import patch

from test_yabause_private_start_sequence import _stage109_instrumented_fixture
from tools.patch_yabause_private_confirm_pad import instrument_full_private_confirm_sequence
from tools.patch_yabause_private_long_window import (
    instrument_full_private_long_window,
    instrument_private_48000_frame_window,
)
from tools.patch_yabause_native_start_bit import MODE_END, MODE_START


def _stage114_fixture():
    return instrument_full_private_confirm_sequence(_stage109_instrumented_fixture())


def _mode(source):
    text = source.decode("utf-8")
    start = text.index(MODE_START)
    end = text.index(MODE_END, start) + len(MODE_END)
    return text[start:end]


class Stage115LongWindowSourceTests(unittest.TestCase):
    def test_extends_only_the_fail_closed_frame_cap(self):
        stage114 = _stage114_fixture()
        patched = instrument_private_48000_frame_window(stage114)
        mode = _mode(patched)
        self.assertEqual(mode.count("frames > 48000"), 1)
        self.assertNotIn("frames > 24000", mode)
        for token in (
            "VH_SATURN_START_AT_FRAME",
            "VH_SATURN_CONFIRM_AT_FRAME",
            "VH_SATURN_CONFIRM_BUTTON",
            "PerPadAPressed(vh107_pad);",
            "PerPadCPressed(vh107_pad);",
            "VH_PADSTATE initial_confirm_button=%c active_low_bit=1",
            "video-state.txt",
            "sh2-window.txt",
            "frames.stats",
        ):
            self.assertIn(token, mode)
        self.assertEqual(patched.count(b"YabauseEmulate()"), stage114.count(b"YabauseEmulate()"))
        self.assertEqual(patched.count(b"vh101_snapshot("), stage114.count(b"vh101_snapshot("))
        self.assertEqual(patched.count(b"vh102_snapshot("), stage114.count(b"vh102_snapshot("))

    def test_rejects_unpinned_missing_or_duplicate_cap(self):
        stage114 = _stage114_fixture()
        for candidate in (
            b"",
            b"int main(){return 0;}",
            stage114.replace(b"frames > 24000", b"frames >= 24000"),
        ):
            with self.subTest(size=len(candidate)), self.assertRaises(ValueError):
                instrument_private_48000_frame_window(candidate)
        with self.assertRaisesRegex(ValueError, "already applied"):
            instrument_private_48000_frame_window(
                instrument_private_48000_frame_window(stage114)
            )

    def test_full_pipeline_composes_confirm_then_long_window(self):
        expected = (
            b"VH_SATURN_START_AT_FRAME VH_SATURN_CONFIRM_AT_FRAME "
            b"VH_SATURN_CONFIRM_BUTTON PerPadCPressed(vh107_pad); "
            b"frames > 48000 video-state.txt sh2-window.txt pad-state.txt"
        )
        with (
            patch(
                "tools.patch_yabause_private_long_window.instrument_full_private_confirm_sequence",
                return_value=b"stage114",
            ) as stage114,
            patch(
                "tools.patch_yabause_private_long_window.instrument_private_48000_frame_window",
                return_value=expected,
            ) as stage115,
        ):
            result = instrument_full_private_long_window(b"pinned-upstream")
        self.assertEqual(result, expected)
        stage114.assert_called_once_with(b"pinned-upstream")
        stage115.assert_called_once_with(b"stage114")


if __name__ == "__main__":
    unittest.main()
