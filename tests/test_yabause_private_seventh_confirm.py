"""Synthetic-only source regressions for Stage122; no original media is used."""
import unittest
from unittest.mock import patch
from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_sixth_confirm import CONFIRM6_PRESS, CONFIRM6_RELEASE
from tools.patch_yabause_private_seventh_confirm import (
    SIXTH_SETUP_END, SETUP_CONFIRM7, instrument_private_seventh_confirm,
    instrument_full_private_seventh_confirm,
)

PAIR = (
    "PerPadCPressed(vh107_pad);\nPerPadCReleased(vh107_pad);\n"
    "VH_PAD frame=%d button=%c action=PRESS\n"
    "VH_PAD frame=%d button=%c action=RELEASE\n"
    "VH_PADSTATE frame=%d button=%c active_low_bit=0\n"
    "VH_PADSTATE frame=%d button=%c active_low_bit=1\n"
)

def synthetic_stage121():
    mode = MODE_START + "\nframes > 72000\n" + SIXTH_SETUP_END + PAIR*5
    mode += CONFIRM6_PRESS + CONFIRM6_RELEASE + EMULATE_START + "YabauseEmulate();\n" + MODE_END
    return ("void fake() {\n" + mode + "\n}\n").encode()

class SeventhConfirmTests(unittest.TestCase):
    def test_injects_guarded_seventh_C_and_84k_cap(self):
        out=instrument_private_seventh_confirm(synthetic_stage121()).decode()
        self.assertEqual(out.count("frames > 84000"),1)
        self.assertNotIn("frames > 72000",out)
        self.assertEqual(out.count("PerPadCPressed(vh107_pad);"),7)
        self.assertEqual(out.count("PerPadCReleased(vh107_pad);"),7)
        self.assertIn("VH_SATURN_CONFIRM_AT_FRAME7",out)
        self.assertIn("VH_SATURN_CONFIRM7_ENABLED",out)
        self.assertIn("vh121_confirm6_enabled != 1",out)
        self.assertIn("frame == vh122_confirm_at7 + 6",out)
    def test_empty_and_invalid_enable_values_fail_closed(self):
        for token in ("vh122_enable7 == NULL","!*vh122_enable7",
                      "vh122_enable7[1] != '\\0'",
                      "vh122_enable7[0] != '0'","vh122_enable7[0] != '1'"):
            self.assertIn(token,SETUP_CONFIRM7)
    def test_invalid_bounds_and_duplicate_patch_are_rejected(self):
        with self.assertRaisesRegex(ValueError,"unpinned"):
            instrument_private_seventh_confirm(b"int main(){}")
        with self.assertRaisesRegex(ValueError,"72,000-frame cap"):
            instrument_private_seventh_confirm(synthetic_stage121().replace(b"frames > 72000",b"frames > 60000"))
        with self.assertRaisesRegex(ValueError,"already instrumented"):
            instrument_private_seventh_confirm(instrument_private_seventh_confirm(synthetic_stage121()))
    def test_seventh_press_must_follow_sixth_and_fit_window(self):
        self.assertIn("n122 < (long)vh121_confirm_at6 + 12L",SETUP_CONFIRM7)
        self.assertIn("n122 > (long)frames - 8L",SETUP_CONFIRM7)
    def test_full_pipeline_composes_from_stage121(self):
        expected=b"VH_SATURN_CONFIRM_AT_FRAME7 VH_SATURN_CONFIRM7_ENABLED frames > 84000 frames.stats video-state.txt sh2-window.txt pad-state.txt"
        with patch("tools.patch_yabause_private_seventh_confirm.instrument_full_private_sixth_confirm",return_value=b"stage121") as sixth, \
             patch("tools.patch_yabause_private_seventh_confirm.instrument_private_seventh_confirm",return_value=expected) as seventh:
            self.assertEqual(instrument_full_private_seventh_confirm(b"pinned upstream"),expected)
        sixth.assert_called_once_with(b"pinned upstream")
        seventh.assert_called_once_with(b"stage121")

if __name__=="__main__":unittest.main()
