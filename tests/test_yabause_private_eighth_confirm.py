"""Synthetic-only source regressions for Stage123; no original media."""
import unittest
from unittest.mock import patch
from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_eighth_confirm import (
    SEVENTH_SETUP_END, SETUP_CONFIRM8, instrument_private_eighth_confirm,
    instrument_full_private_eighth_confirm,
)

PAIR = (
    "PerPadCPressed(vh107_pad);\nPerPadCReleased(vh107_pad);\n"
    "VH_PAD frame=%d button=%c action=PRESS\n"
    "VH_PAD frame=%d button=%c action=RELEASE\n"
    "VH_PADSTATE frame=%d button=%c active_low_bit=0\n"
    "VH_PADSTATE frame=%d button=%c active_low_bit=1\n"
)

def synthetic_stage122():
    mode=MODE_START+"\nframes > 84000\n"+SEVENTH_SETUP_END+PAIR*7
    mode+=EMULATE_START+" return 1;\n"+MODE_END
    return ("void fake() {\n"+mode+"\n}\n").encode()

class EighthConfirmTests(unittest.TestCase):
    def test_injects_guarded_eighth_C_and_96k_cap(self):
        out=instrument_private_eighth_confirm(synthetic_stage122()).decode()
        self.assertEqual(out.count("frames > 96000"),1)
        self.assertNotIn("frames > 84000",out)
        self.assertEqual(out.count("PerPadCPressed(vh107_pad);"),8)
        self.assertEqual(out.count("PerPadCReleased(vh107_pad);"),8)
        self.assertIn("VH_SATURN_CONFIRM_AT_FRAME8",out)
        self.assertIn("VH_SATURN_CONFIRM8_ENABLED",out)
        self.assertIn("vh122_confirm7_enabled != 1",out)
        self.assertIn("frame == vh123_confirm_at8 + 6",out)
    def test_empty_and_invalid_enable_values_fail_closed(self):
        for token in ("vh123_at8 == NULL","!*vh123_at8","vh123_enable8 == NULL",
                      "!*vh123_enable8","vh123_enable8[1] != '\\0'",
                      "vh123_enable8[0] != '0'","vh123_enable8[0] != '1'"):
            self.assertIn(token,SETUP_CONFIRM8)
    def test_invalid_bounds_and_duplicate_patch_are_rejected(self):
        with self.assertRaisesRegex(ValueError,"unpinned"):
            instrument_private_eighth_confirm(b"int main(){}")
        with self.assertRaisesRegex(ValueError,"84,000-frame cap"):
            instrument_private_eighth_confirm(synthetic_stage122().replace(b"frames > 84000",b"frames > 72000"))
        with self.assertRaisesRegex(ValueError,"already instrumented"):
            instrument_private_eighth_confirm(instrument_private_eighth_confirm(synthetic_stage122()))
    def test_eighth_press_must_follow_seventh_and_fit_window(self):
        self.assertIn("n123 < (long)vh122_confirm_at7 + 12L",SETUP_CONFIRM8)
        self.assertIn("n123 > (long)frames - 8L",SETUP_CONFIRM8)
    def test_full_pipeline_composes_stage122_then_eighth_confirm(self):
        expected=(b"VH_SATURN_START_AT_FRAME VH_SATURN_CONFIRM_AT_FRAME6 VH_SATURN_CONFIRM6_ENABLED "
                  b"VH_SATURN_CONFIRM_AT_FRAME7 VH_SATURN_CONFIRM7_ENABLED VH_SATURN_CONFIRM_AT_FRAME8 "
                  b"VH_SATURN_CONFIRM8_ENABLED frames > 96000 frames.stats video-state.txt sh2-window.txt pad-state.txt")
        with patch("tools.patch_yabause_private_eighth_confirm.instrument_full_private_seventh_confirm",return_value=b"stage122") as seventh, \
             patch("tools.patch_yabause_private_eighth_confirm.instrument_private_eighth_confirm",return_value=expected) as eighth:
            self.assertEqual(instrument_full_private_eighth_confirm(b"pinned upstream"),expected)
        seventh.assert_called_once_with(b"pinned upstream")
        eighth.assert_called_once_with(b"stage122")

if __name__=="__main__":unittest.main()
