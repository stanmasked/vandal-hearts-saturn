"""ROM-free tests for the Stage121 sixth-C source patcher."""
import unittest
from unittest.mock import patch
from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_sixth_confirm import (
    FIFTH_SETUP_END, SETUP_CONFIRM6,
    instrument_private_sixth_confirm, instrument_full_private_sixth_confirm,
)

def synthetic_stage119():
    pair=(
        "PerPadCPressed(vh107_pad);\n"
        "PerPadCReleased(vh107_pad);\n"
        "VH_PAD frame=%d button=%c action=PRESS\n"
        "VH_PAD frame=%d button=%c action=RELEASE\n"
        "VH_PADSTATE frame=%d button=%c active_low_bit=0\n"
        "VH_PADSTATE frame=%d button=%c active_low_bit=1\n"
    )
    mode=MODE_START + "\nframes > 60000\n" + FIFTH_SETUP_END + pair*5 + EMULATE_START + "\n" + MODE_END
    return ("void fake() {\n"+mode+"\n}\n").encode()

class SixthConfirmSourceTests(unittest.TestCase):
    def test_injects_optional_sixth_and_bounds(self):
        original=synthetic_stage119()
        out=instrument_private_sixth_confirm(original)
        mode=out.decode()
        self.assertEqual(mode.count("frames > 72000"),1)
        self.assertNotIn("frames > 60000",mode)
        self.assertEqual(mode.count("PerPadCPressed(vh107_pad);"),6)
        self.assertEqual(mode.count("PerPadCReleased(vh107_pad);"),6)
        self.assertEqual(mode.count("VH_SATURN_CONFIRM_AT_FRAME6"),1)
        self.assertEqual(mode.count("VH_SATURN_CONFIRM6_ENABLED"),1)
        self.assertIn("frame == vh121_confirm_at6 + 6",mode)
        self.assertIn("vh119_confirm5_enabled != 1",mode)
    def test_missing_and_empty_enable_flag_rejected(self):
        for token in ("vh121_enable6 == NULL","!*vh121_enable6",
                      "vh121_enable6[1] !=","vh121_enable6[0] != '0'","vh121_enable6[0] != '1'"):
            self.assertIn(token,SETUP_CONFIRM6)
    def test_rejects_unpinned_stale_or_repeat_patch(self):
        with self.assertRaisesRegex(ValueError,"unpinned"):
            instrument_private_sixth_confirm(b"int main(){}")
        s=synthetic_stage119()
        with self.assertRaisesRegex(ValueError,"60,000-frame cap"):
            instrument_private_sixth_confirm(s.replace(b"frames > 60000",b"frames > 48000"))
        with self.assertRaisesRegex(ValueError,"already instrumented"):
            instrument_private_sixth_confirm(instrument_private_sixth_confirm(s))
    def test_fifth_schedule_order_and_bound(self):
        for token in ("n121 < (long)vh119_confirm_at5 + 12L","n121 > (long)frames - 8L"):
            self.assertIn(token,SETUP_CONFIRM6)
    def test_full_pipeline_composes_before_patching_sixth(self):
        expected=b"VH_SATURN_START_AT_FRAME VH_SATURN_CONFIRM_AT_FRAME5 VH_SATURN_CONFIRM5_ENABLED VH_SATURN_CONFIRM_AT_FRAME6 VH_SATURN_CONFIRM6_ENABLED frames > 72000 frames.stats video-state.txt sh2-window.txt pad-state.txt"
        with (patch("tools.patch_yabause_private_sixth_confirm.instrument_full_private_fifth_confirm",return_value=b"stage119") as fifth,
              patch("tools.patch_yabause_private_sixth_confirm.instrument_private_sixth_confirm",return_value=expected) as sixth):
            self.assertEqual(instrument_full_private_sixth_confirm(b"pinned upstream"),expected)
        fifth.assert_called_once_with(b"pinned upstream")
        sixth.assert_called_once_with(b"stage119")

if __name__=="__main__":unittest.main()
