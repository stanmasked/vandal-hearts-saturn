"""Synthetic-only source regressions for Stage124; no original media."""
import unittest
from unittest.mock import patch
from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_ninth_confirm import (
    EIGHTH_SETUP_END, SETUP_CONFIRM9, instrument_private_ninth_confirm,
    instrument_full_private_ninth_confirm,
)

PAIR = (
    "PerPadCPressed(vh107_pad);\nPerPadCReleased(vh107_pad);\n"
    "VH_PAD frame=%d button=%c action=PRESS\n"
    "VH_PAD frame=%d button=%c action=RELEASE\n"
    "VH_PADSTATE frame=%d button=%c active_low_bit=0\n"
    "VH_PADSTATE frame=%d button=%c active_low_bit=1\n"
)

def synthetic_stage123():
    mode=MODE_START+"\nframes > 96000\n"+EIGHTH_SETUP_END+PAIR*8
    mode+=EMULATE_START+" return 1;\n"+MODE_END
    return ("void fake() {\n"+mode+"\n}\n").encode()

class NinthConfirmTests(unittest.TestCase):
    def test_injects_guarded_ninth_C_and_108k_cap(self):
        out=instrument_private_ninth_confirm(synthetic_stage123()).decode()
        self.assertEqual(out.count("frames > 108000"),1)
        self.assertNotIn("frames > 96000",out)
        self.assertEqual(out.count("PerPadCPressed(vh107_pad);"),9)
        self.assertEqual(out.count("PerPadCReleased(vh107_pad);"),9)
        self.assertIn("VH_SATURN_CONFIRM_AT_FRAME9",out)
        self.assertIn("VH_SATURN_CONFIRM9_ENABLED",out)
        self.assertIn("vh123_confirm8_enabled != 1",out)
        self.assertIn("frame == vh124_confirm_at9 + 6",out)
    def test_empty_and_invalid_enable_values_fail_closed(self):
        for token in ("vh124_at9 == NULL","!*vh124_at9","vh124_enable9 == NULL",
                      "!*vh124_enable9","vh124_enable9[1] != '\\0'",
                      "vh124_enable9[0] != '0'","vh124_enable9[0] != '1'"):
            self.assertIn(token,SETUP_CONFIRM9)
    def test_invalid_bounds_and_duplicate_patch_are_rejected(self):
        with self.assertRaisesRegex(ValueError,"unpinned"):
            instrument_private_ninth_confirm(b"int main(){}")
        with self.assertRaisesRegex(ValueError,"96,000-frame cap"):
            instrument_private_ninth_confirm(synthetic_stage123().replace(b"frames > 96000",b"frames > 84000"))
        with self.assertRaisesRegex(ValueError,"already instrumented"):
            instrument_private_ninth_confirm(instrument_private_ninth_confirm(synthetic_stage123()))
    def test_ninth_press_must_follow_eighth_and_fit_window(self):
        self.assertIn("n124 < (long)vh123_confirm_at8 + 12L",SETUP_CONFIRM9)
        self.assertIn("n124 > (long)frames - 8L",SETUP_CONFIRM9)
    def test_full_pipeline_composes_stage123_then_ninth_confirm(self):
        expected=(b"VH_SATURN_START_AT_FRAME VH_SATURN_CONFIRM_AT_FRAME7 VH_SATURN_CONFIRM7_ENABLED "
                  b"VH_SATURN_CONFIRM_AT_FRAME8 VH_SATURN_CONFIRM8_ENABLED VH_SATURN_CONFIRM_AT_FRAME9 "
                  b"VH_SATURN_CONFIRM9_ENABLED frames > 108000 frames.stats video-state.txt sh2-window.txt pad-state.txt")
        with patch("tools.patch_yabause_private_ninth_confirm.instrument_full_private_eighth_confirm",return_value=b"stage123") as eighth, \
             patch("tools.patch_yabause_private_ninth_confirm.instrument_private_ninth_confirm",return_value=expected) as ninth:
            self.assertEqual(instrument_full_private_ninth_confirm(b"pinned upstream"),expected)
        eighth.assert_called_once_with(b"pinned upstream")
        ninth.assert_called_once_with(b"stage123")

if __name__=="__main__":unittest.main()
