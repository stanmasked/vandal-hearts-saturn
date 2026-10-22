"""Synthetic-only source tests for the Stage117 third C pulse."""
import unittest
from unittest.mock import patch

from test_yabause_private_second_confirm import _stage115_fixture, _mode
from tools.patch_yabause_private_second_confirm import instrument_private_second_confirm
from tools.patch_yabause_private_third_confirm import (
    instrument_full_private_third_confirm,
    instrument_private_third_confirm,
)


def _stage116_fixture():
    return instrument_private_second_confirm(_stage115_fixture())


class Stage117ThirdConfirmSourceTests(unittest.TestCase):
    def test_adds_optional_third_c_pulse_and_preserves_48k_runner(self):
        stage116 = _stage116_fixture()
        patched = instrument_private_third_confirm(stage116)
        mode = _mode(patched)
        self.assertEqual(mode.count("frames > 48000"), 1)
        self.assertEqual(mode.count("VH_SATURN_CONFIRM_AT_FRAME3"), 1)
        self.assertEqual(mode.count("vh117_confirm_at3"), 6)
        self.assertEqual(mode.count("PerPadCPressed(vh107_pad);"), 3)
        self.assertEqual(mode.count("PerPadCReleased(vh107_pad);"), 3)
        self.assertIn("vh116_confirm_at2 < 0", mode)
        self.assertIn("vh114_confirm_button != 'C'", mode)
        self.assertIn("n117 < (long)vh116_confirm_at2 + 12L", mode)
        self.assertIn("n117 > (long)frames - 8L", mode)
        self.assertIn("const unsigned char vh117_mask = 0x02U;", mode)
        self.assertEqual(patched.count(b"YabauseEmulate()"), stage116.count(b"YabauseEmulate()"))
        self.assertEqual(patched.count(b"vh101_snapshot("), stage116.count(b"vh101_snapshot("))
        self.assertEqual(patched.count(b"vh102_snapshot("), stage116.count(b"vh102_snapshot("))

    def test_rejects_duplicate_or_unpinned_third_confirm_patch(self):
        stage116 = _stage116_fixture()
        for candidate in (
            b"",
            b"int main(){return 0;}",
            stage116.replace(b"frames > 48000", b"frames >= 48000"),
        ):
            with self.subTest(size=len(candidate)), self.assertRaises(ValueError):
                instrument_private_third_confirm(candidate)
        with self.assertRaisesRegex(ValueError, "already instrumented"):
            instrument_private_third_confirm(instrument_private_third_confirm(stage116))

    def test_full_pipeline_composes_stage116_then_third_confirm(self):
        expected = (
            b"VH_SATURN_CONFIRM_AT_FRAME VH_SATURN_CONFIRM_AT_FRAME2 "
            b"VH_SATURN_CONFIRM_AT_FRAME3 VH_SATURN_CONFIRM_BUTTON "
            b"frames > 48000 frames.stats video-state.txt sh2-window.txt pad-state.txt"
        )
        with (
            patch(
                "tools.patch_yabause_private_third_confirm.instrument_full_private_second_confirm",
                return_value=b"stage116",
            ) as stage116,
            patch(
                "tools.patch_yabause_private_third_confirm.instrument_private_third_confirm",
                return_value=expected,
            ) as stage117,
        ):
            result = instrument_full_private_third_confirm(b"pinned-upstream")
        self.assertEqual(result, expected)
        stage116.assert_called_once_with(b"pinned-upstream")
        stage117.assert_called_once_with(b"stage116")


if __name__ == "__main__":
    unittest.main()
