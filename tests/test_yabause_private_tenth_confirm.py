"""Synthetic-only Stage125 source regressions; absolutely no original media."""
import unittest
from unittest.mock import patch

from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_tenth_confirm import (
    NINTH_SETUP_END, SETUP_CONFIRM10,
    instrument_private_tenth_confirm, instrument_full_private_tenth_confirm,
)

PAIR = (
    "PerPadCPressed(vh107_pad);\nPerPadCReleased(vh107_pad);\n"
    "VH_PAD frame=%d button=%c action=PRESS\n"
    "VH_PAD frame=%d button=%c action=RELEASE\n"
    "VH_PADSTATE frame=%d button=%c active_low_bit=0\n"
    "VH_PADSTATE frame=%d button=%c active_low_bit=1\n"
)

def synthetic_stage124():
    mode = MODE_START + "\nframes > 108000\n" + NINTH_SETUP_END + PAIR * 9
    mode += EMULATE_START + " return 1;\n" + MODE_END
    return ("void fake() {\n" + mode + "\n}\n").encode("utf-8")

class TenthConfirmTests(unittest.TestCase):
    def test_tenth_press_and_release_and_120k_cap(self):
        result = instrument_private_tenth_confirm(synthetic_stage124()).decode()
        self.assertEqual(result.count("frames > 120000"), 1)
        self.assertNotIn("frames > 108000", result)
        self.assertEqual(result.count("PerPadCPressed(vh107_pad);"), 10)
        self.assertEqual(result.count("PerPadCReleased(vh107_pad);"), 10)
        self.assertIn("VH_SATURN_CONFIRM_AT_FRAME10", result)
        self.assertIn("VH_SATURN_CONFIRM10_ENABLED", result)
        self.assertIn("vh124_confirm9_enabled != 1", result)
        self.assertIn("frame == vh125_confirm_at10 + 6", result)
    def test_frame_and_enable_must_be_explicit_and_canonical(self):
        for token in (
            "vh125_at10 == NULL", "vh125_enable10 == NULL",
            "!*vh125_at10", "!*vh125_enable10",
            "vh125_enable10[1] != '\\0'", "vh125_enable10[0] != '0'",
            "vh125_enable10[0] != '1'", "endptr125 == vh125_at10",
            "*endptr125 != '\\0'",
        ):
            self.assertIn(token, SETUP_CONFIRM10)
    def test_tenth_requires_prior_ninth_and_has_release_slack(self):
        self.assertIn("vh124_confirm9_enabled != 1", SETUP_CONFIRM10)
        self.assertIn("n125 < (long)vh124_confirm_at9 + 12L", SETUP_CONFIRM10)
        self.assertIn("n125 > (long)frames - 8L", SETUP_CONFIRM10)
    def test_reject_missing_anchor_changed_cap_duplicate_patching(self):
        with self.assertRaisesRegex(ValueError, "unpinned"):
            instrument_private_tenth_confirm(b"int main(){}")
        with self.assertRaisesRegex(ValueError, "108,000-frame cap"):
            instrument_private_tenth_confirm(synthetic_stage124().replace(
                b"frames > 108000", b"frames > 96000"))
        with self.assertRaisesRegex(ValueError, "source anchors differ"):
            instrument_private_tenth_confirm(synthetic_stage124().replace(
                b"vh124_confirm9_enabled", b"vh124_confirm9_broken"))
        with self.assertRaisesRegex(ValueError, "already instrumented"):
            instrument_private_tenth_confirm(
                instrument_private_tenth_confirm(synthetic_stage124()))
    def test_cannot_accept_missing_inherited_ninth_pair(self):
        with self.assertRaisesRegex(ValueError, "incomplete Stage125"):
            instrument_private_tenth_confirm(synthetic_stage124().replace(
                PAIR.encode(), b"", 1))
    def test_full_pipeline_composes_pinned_stage124_and_tenth(self):
        fake = (b"VH_SATURN_START_AT_FRAME VH_SATURN_CONFIRM_AT_FRAME8 "
                b"VH_SATURN_CONFIRM8_ENABLED VH_SATURN_CONFIRM_AT_FRAME9 "
                b"VH_SATURN_CONFIRM9_ENABLED VH_SATURN_CONFIRM_AT_FRAME10 "
                b"VH_SATURN_CONFIRM10_ENABLED frames > 120000 frames.stats "
                b"video-state.txt sh2-window.txt pad-state.txt")
        with patch(
            "tools.patch_yabause_private_tenth_confirm.instrument_full_private_ninth_confirm",
            return_value=b"stage124",
        ) as ninth, patch(
            "tools.patch_yabause_private_tenth_confirm.instrument_private_tenth_confirm",
            return_value=fake,
        ) as tenth:
            self.assertEqual(instrument_full_private_tenth_confirm(b"pinned upstream"), fake)
        ninth.assert_called_once_with(b"pinned upstream")
        tenth.assert_called_once_with(b"stage124")

if __name__ == "__main__":
    unittest.main()
