"""Synthetic-only source-contract tests for Stage114 A/C confirm input."""
import unittest
from unittest.mock import patch

from test_yabause_private_start_sequence import _stage109_instrumented_fixture
from tools.patch_yabause_private_start_sequence import instrument_private_start_sequence
from tools.patch_yabause_private_confirm_pad import (
    CONFIRM_INITIAL, CONFIRM_PRESS, CONFIRM_RELEASE, SETUP_CONFIRM,
    instrument_full_private_confirm_sequence, instrument_private_confirm_button,
)


def _stage112_fixture():
    return instrument_private_start_sequence(_stage109_instrumented_fixture())


class Stage114ConfirmPadSourceTests(unittest.TestCase):
    def test_adds_native_a_and_c_press_release_with_active_low_checks(self):
        source = instrument_private_confirm_button(_stage112_fixture()).decode()
        self.assertIn('getenv("VH_SATURN_CONFIRM_AT_FRAME")', source)
        self.assertIn('getenv("VH_SATURN_CONFIRM_BUTTON")', source)
        self.assertIn("PerPadAPressed(vh107_pad);", source)
        self.assertIn("PerPadAReleased(vh107_pad);", source)
        self.assertIn("PerPadCPressed(vh107_pad);", source)
        self.assertIn("PerPadCReleased(vh107_pad);", source)
        self.assertIn("0x04U", source)
        self.assertIn("0x02U", source)
        self.assertIn("frame == vh114_confirm_at + 6", source)
        self.assertIn("VH_PADSTATE initial_confirm_button=%c active_low_bit=1", source)
        self.assertIn("VH_PADSTATE frame=%d button=%c active_low_bit=0", source)
        self.assertIn("VH_PADSTATE frame=%d button=%c active_low_bit=1", source)
        self.assertIn("frames > 24000", source)
        self.assertEqual(source.count("YabauseEmulate()"), 2)
        self.assertEqual(source.count("vh101_snapshot("), 4)
        self.assertEqual(source.count("vh102_snapshot("), 4)

    def test_confirm_requires_a_single_a_or_c_and_first_start(self):
        self.assertIn("vh114_at != NULL || vh114_button_env != NULL", SETUP_CONFIRM)
        self.assertIn("!vh114_at || !*vh114_at || !vh114_button_env", SETUP_CONFIRM)
        self.assertIn("vh114_button_env[0] != 'A' && vh114_button_env[0] != 'C'", SETUP_CONFIRM)
        self.assertIn("vh114_button_env[1] != '\\0'", SETUP_CONFIRM)
        self.assertIn("vh107_start_at < 0", SETUP_CONFIRM)
        self.assertIn("vh112_start_at2 >= 0", SETUP_CONFIRM)
        self.assertIn("n114 < (long)vh107_start_at + 12L", SETUP_CONFIRM)
        self.assertIn("n114 > (long)frames - 8L", SETUP_CONFIRM)

    def test_confirm_press_and_release_receipts_are_numeric_and_local(self):
        for block in (CONFIRM_PRESS, CONFIRM_RELEASE):
            self.assertIn("VH_PAD frame=%d button=%c action=", block)
            self.assertIn("VH_PADSTATE frame=%d button=%c active_low_bit=", block)
            self.assertNotIn("fwrite(", block)
            self.assertNotIn("upload", block.lower())
            self.assertNotIn("screenshot", block.lower())
        self.assertIn("PerPadAPressed(vh107_pad);", CONFIRM_PRESS)
        self.assertIn("PerPadCPressed(vh107_pad);", CONFIRM_PRESS)
        self.assertIn("PerPadAReleased(vh107_pad);", CONFIRM_RELEASE)
        self.assertIn("PerPadCReleased(vh107_pad);", CONFIRM_RELEASE)
        self.assertIn("initial_confirm_button=%c active_low_bit=1", CONFIRM_INITIAL)

    def test_rejects_tampered_or_duplicate_stage112_source(self):
        raw = _stage112_fixture()
        for candidate in (
            b"",
            b"int main(){return 0;}",
            raw.replace(b"PerPadStartPressed(vh107_pad);", b"PerPadPressTampered(vh107_pad);"),
            raw.replace(b"if (YabauseEmulate() != 0)", b"if (YabauseEmulateTampered() != 0)"),
        ):
            with self.subTest(size=len(candidate)), self.assertRaises(ValueError):
                instrument_private_confirm_button(candidate)
        with self.assertRaisesRegex(ValueError, "already instrumented"):
            instrument_private_confirm_button(instrument_private_confirm_button(raw))

    def test_full_pipeline_keeps_stage112_before_confirm(self):
        complete = (
            b"VH_SATURN_START_AT_FRAME VH_SATURN_START_AT_FRAME2 "
            b"VH_SATURN_CONFIRM_AT_FRAME VH_SATURN_CONFIRM_BUTTON "
            b"PerPadAPressed(vh107_pad); PerPadCPressed(vh107_pad); "
            b"frames > 24000 video-state.txt sh2-window.txt pad-state.txt"
        )
        with (
            patch(
                "tools.patch_yabause_private_confirm_pad.instrument_full_private_start_sequence",
                return_value=b"stage112",
            ) as stage112,
            patch(
                "tools.patch_yabause_private_confirm_pad.instrument_private_confirm_button",
                return_value=complete,
            ) as stage114,
        ):
            result = instrument_full_private_confirm_sequence(b"pinned-upstream")
        self.assertEqual(result, complete)
        stage112.assert_called_once_with(b"pinned-upstream")
        stage114.assert_called_once_with(b"stage112")


if __name__ == "__main__":
    unittest.main()
