"""Synthetic-only source tests for the Stage116 follow-up C input."""
import unittest
from unittest.mock import patch

from test_yabause_private_start_sequence import _stage109_instrumented_fixture
from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_confirm_pad import instrument_private_confirm_button
from tools.patch_yabause_private_followup_c import (
    FOLLOWUP_PRESS,
    FOLLOWUP_RELEASE,
    SETUP_FOLLOWUP,
    instrument_full_private_followup_c,
    instrument_private_followup_c,
)
from tools.patch_yabause_private_long_window import instrument_private_48000_frame_window
from tools.patch_yabause_private_start_sequence import instrument_private_start_sequence


def _stage115_fixture():
    stage112 = instrument_private_start_sequence(_stage109_instrumented_fixture())
    stage114 = instrument_private_confirm_button(stage112)
    return instrument_private_48000_frame_window(stage114)


def _mode(source):
    text = source.decode("utf-8")
    start = text.index(MODE_START)
    end = text.index(MODE_END, start) + len(MODE_END)
    return text[start:end]


class Stage116FollowupCSourceTests(unittest.TestCase):
    def test_adds_one_optional_c_press_release_and_preserves_stage115(self):
        stage115 = _stage115_fixture()
        result = instrument_private_followup_c(stage115)
        mode = _mode(result)
        self.assertIn("frames > 48000", mode)
        self.assertNotIn("frames > 24000", mode)
        self.assertEqual(mode.count("VH_SATURN_FOLLOWUP_C_AT_FRAME"), 1)
        self.assertEqual(mode.count("PerPadCPressed(vh107_pad);"), 2)
        self.assertEqual(mode.count("PerPadCReleased(vh107_pad);"), 2)
        self.assertEqual(mode.count("VH_PAD frame=%d button=C action=PRESS"), 2)
        self.assertEqual(mode.count("VH_PAD frame=%d button=C action=RELEASE"), 2)
        self.assertEqual(mode.count("YabauseEmulate()"), 1)
        self.assertEqual(result.count(b"vh101_snapshot("), stage115.count(b"vh101_snapshot("))
        self.assertEqual(result.count(b"vh102_snapshot("), stage115.count(b"vh102_snapshot("))
        self.assertLess(mode.index(FOLLOWUP_PRESS), mode.index("if (YabauseEmulate() != 0)"))
        self.assertLess(mode.index(FOLLOWUP_RELEASE), mode.index("if (YabauseEmulate() != 0"))

    def test_followup_is_guarded_by_initial_c_and_second_start_exclusion(self):
        for token in (
            "vh114_confirm_at < 0",
            "vh114_confirm_button != 'C'",
            "vh112_start_at2 >= 0",
            "n116 < (long)vh114_confirm_at + 12L",
            "n116 > (long)frames - 8L",
        ):
            self.assertIn(token, SETUP_FOLLOWUP)

    def test_rejects_reapplication_or_missing_stage115_bound(self):
        stage115 = _stage115_fixture()
        with self.assertRaisesRegex(ValueError, "already instrumented"):
            instrument_private_followup_c(instrument_private_followup_c(stage115))
        with self.assertRaisesRegex(ValueError, "unpinned"):
            instrument_private_followup_c(b"int main(){return 0;}")
        unbounded = stage115.replace(b"frames > 48000", b"frames >= 48000")
        with self.assertRaisesRegex(ValueError, "bound differs"):
            instrument_private_followup_c(unbounded)

    def test_full_pipeline_composes_stage115_then_followup(self):
        expected = b"VH_SATURN_FOLLOWUP_C_AT_FRAME frames > 48000 PerPadCReleased(vh107_pad);"
        with (
            patch(
                "tools.patch_yabause_private_followup_c.instrument_full_private_long_window",
                return_value=b"stage115",
            ) as stage115,
            patch(
                "tools.patch_yabause_private_followup_c.instrument_private_followup_c",
                return_value=expected,
            ) as stage116,
        ):
            result = instrument_full_private_followup_c(b"pinned-upstream")
        self.assertEqual(result, expected)
        stage115.assert_called_once_with(b"pinned-upstream")
        stage116.assert_called_once_with(b"stage115")


if __name__ == "__main__":
    unittest.main()
