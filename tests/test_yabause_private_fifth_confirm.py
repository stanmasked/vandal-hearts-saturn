"""Invented-only tests for Stage119 fifth-C source instrumentation."""
import unittest
from unittest.mock import patch

from test_yabause_private_fourth_confirm import _stage117_fixture
from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_fourth_confirm import instrument_private_fourth_confirm
from tools.patch_yabause_private_fifth_confirm import (
    SETUP_CONFIRM5, instrument_private_fifth_confirm,
    instrument_full_private_fifth_confirm,
)


def _stage118_fixture():
    return instrument_private_fourth_confirm(_stage117_fixture())


def _mode(raw):
    text = raw.decode("utf-8")
    a = text.index(MODE_START)
    b = text.index(MODE_END, a) + len(MODE_END)
    return text[a:b]


class Stage119FifthConfirmSourceTests(unittest.TestCase):
    def test_adds_fifth_c_and_preserves_frame_pipeline(self):
        stage118 = _stage118_fixture()
        stage119 = instrument_private_fifth_confirm(stage118)
        mode = _mode(stage119)
        for token, count in (
            ("VH_SATURN_CONFIRM_AT_FRAME5", 1),
            ("VH_SATURN_CONFIRM5_ENABLED", 1),
            ("vh119_confirm_at5", 6),
            ("vh119_confirm5_enabled", 4),
            ("PerPadCPressed(vh107_pad);", 5),
            ("PerPadCReleased(vh107_pad);", 5),
            ("VH_PAD frame=%d button=%c action=PRESS", 5),
            ("VH_PADSTATE frame=%d button=%c active_low_bit=1", 5),
            ("YabauseEmulate()", 1),
        ):
            self.assertEqual(mode.count(token), count)
        self.assertEqual(stage119.count(b"vh101_snapshot("), stage118.count(b"vh101_snapshot("))
        self.assertEqual(stage119.count(b"vh102_snapshot("), stage118.count(b"vh102_snapshot("))
        self.assertIn("frames > 48000", mode)

    def test_fifth_c_guard_requires_enabled_fourth_c(self):
        for token in (
            "vh118_confirm_at4 < 0",
            "vh118_confirm4_enabled != 1",
            "n119 < (long)vh118_confirm_at4 + 12L",
            "n119 > (long)frames - 8L",
            "vh119_enable5[0] != '0'",
            "vh119_enable5[0] != '1'",
        ):
            self.assertIn(token, SETUP_CONFIRM5)

    def test_rejects_unpinned_and_double_patch(self):
        with self.assertRaisesRegex(ValueError, "unpinned"):
            instrument_private_fifth_confirm(b"int main(){return 0;}")
        first = instrument_private_fifth_confirm(_stage118_fixture())
        with self.assertRaisesRegex(ValueError, "already instrumented"):
            instrument_private_fifth_confirm(first)

    def test_full_pipeline_keeps_all_schedules(self):
        expected = (
            b"VH_SATURN_START_AT_FRAME VH_SATURN_CONFIRM_AT_FRAME "
            b"VH_SATURN_CONFIRM_AT_FRAME2 VH_SATURN_CONFIRM2_ENABLED "
            b"VH_SATURN_CONFIRM_AT_FRAME3 VH_SATURN_CONFIRM3_ENABLED "
            b"VH_SATURN_CONFIRM_AT_FRAME4 VH_SATURN_CONFIRM4_ENABLED "
            b"VH_SATURN_CONFIRM_AT_FRAME5 VH_SATURN_CONFIRM5_ENABLED "
            b"frames > 48000 frames.stats video-state.txt sh2-window.txt pad-state.txt"
        )
        with (
            patch("tools.patch_yabause_private_fifth_confirm.instrument_full_private_fourth_confirm",
                  return_value=b"stage118") as stage118,
            patch("tools.patch_yabause_private_fifth_confirm.instrument_private_fifth_confirm",
                  return_value=expected) as stage119,
        ):
            self.assertEqual(instrument_full_private_fifth_confirm(b"public-upstream"), expected)
        stage118.assert_called_once_with(b"public-upstream")
        stage119.assert_called_once_with(b"stage118")


if __name__ == "__main__":
    unittest.main()
