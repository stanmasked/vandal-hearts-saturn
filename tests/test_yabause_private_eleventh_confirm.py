"""Synthetic-only Stage144 patcher contract tests; no original media."""
import unittest

from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_tenth_confirm import SETUP_CONFIRM10, CONFIRM10_PRESS, CONFIRM10_RELEASE
from tools.patch_yabause_private_eleventh_confirm import (
    SETUP_CONFIRM11, CONFIRM11_PRESS, CONFIRM11_RELEASE,
    instrument_private_eleventh_confirm_on_stage143,
)


def fixture():
    prior = []
    for _ in range(9):
        prior.extend((
            "         PerPadCPressed(vh107_pad);\n",
            '         fprintf(vh107_pad_log, "VH_PAD frame=%d button=%c action=PRESS\\n", frame, \\'C\\');\n',
            '         fprintf(vh109_state_log, "VH_PADSTATE frame=%d button=%c active_low_bit=0\\n", frame, \\'C\\');\n',
            "         PerPadCReleased(vh107_pad);\n",
            '         fprintf(vh107_pad_log, "VH_PAD frame=%d button=%c action=RELEASE\\n", frame, \\'C\\');\n',
            '         fprintf(vh109_state_log, "VH_PADSTATE frame=%d button=%c active_low_bit=1\\n", frame, \\'C\\');\n',
        ))
    mode = (
        "         if (frames > 120000) return 1;\n"
        "         /* VH_STAGE143_DURABLE_PAD_RECEIPTS */\n"
        "         setvbuf(vh107_pad_log, NULL, _IONBF, 0);\n"
        "         setvbuf(vh109_state_log, NULL, _IONBF, 0);\n"
        + SETUP_CONFIRM10
        + "".join(prior)
        + CONFIRM10_PRESS
        + CONFIRM10_RELEASE
        + EMULATE_START
    )
    return "#include <stdio.h>\nOUTSIDE_PREFIX\n" + MODE_START + mode + MODE_END + "\nOUTSIDE_SUFFIX\n"


class EleventhConfirmPatchTests(unittest.TestCase):
    def test_adds_eleventh_c_and_extends_cap(self):
        original = fixture()
        patched = instrument_private_eleventh_confirm_on_stage143(original.encode()).decode()
        self.assertEqual(patched.count("frames > 132000"), 1)
        self.assertNotIn("frames > 120000", patched)
        self.assertEqual(patched.count("VH_SATURN_CONFIRM_AT_FRAME11"), 1)
        self.assertEqual(patched.count("VH_SATURN_CONFIRM11_ENABLED"), 1)
        self.assertEqual(patched.count("vh126_confirm_at11"), 6)
        self.assertEqual(patched.count("vh126_confirm11_enabled"), 4)
        self.assertEqual(patched.count("PerPadCPressed(vh107_pad);"), 11)
        self.assertEqual(patched.count("PerPadCReleased(vh107_pad);"), 11)
        self.assertEqual(patched.count("VH_PAD frame=%d button=%c action=PRESS"), 11)
        self.assertEqual(patched.count("VH_PAD frame=%d button=%c action=RELEASE"), 11)
        self.assertEqual(patched.count("VH_PADSTATE frame=%d button=%c active_low_bit=0"), 11)
        self.assertEqual(patched.count("VH_PADSTATE frame=%d button=%c active_low_bit=1"), 11)

    def test_requires_shared_tenth_c_before_eleventh_c(self):
        self.assertIn("vh125_confirm_at10 < 0 || vh125_confirm10_enabled != 1", SETUP_CONFIRM11)
        self.assertIn("n126 < (long)vh125_confirm_at10 + 12L", SETUP_CONFIRM11)
        self.assertIn("n126 > (long)frames - 8L", SETUP_CONFIRM11)

    def test_only_intervention_guarded_events_are_added(self):
        patched = instrument_private_eleventh_confirm_on_stage143(fixture().encode()).decode()
        self.assertIn("if (vh126_confirm11_enabled)", patched)
        self.assertIn("frame == vh126_confirm_at11", patched)
        self.assertIn("frame == vh126_confirm_at11 + 6", patched)
        self.assertIn("PerPadCPressed(vh107_pad);", CONFIRM11_PRESS)
        self.assertIn("PerPadCReleased(vh107_pad);", CONFIRM11_RELEASE)

    def test_source_outside_private_mode_is_unchanged(self):
        original = fixture()
        patched = instrument_private_eleventh_confirm_on_stage143(original.encode()).decode()
        self.assertTrue(patched.startswith("#include <stdio.h>\nOUTSIDE_PREFIX\n"))
        self.assertTrue(patched.endswith("\nOUTSIDE_SUFFIX\n"))

    def test_missing_stage143_receipt_marker_fails_closed(self):
        original = fixture().replace("VH_STAGE143_DURABLE_PAD_RECEIPTS", "WRONG_MARKER", 1)
        with self.assertRaisesRegex(ValueError, "Stage143 unbuffered PAD"):
            instrument_private_eleventh_confirm_on_stage143(original.encode())

    def test_wrong_frame_cap_fails_closed(self):
        original = fixture().replace("frames > 120000", "frames > 108000", 1)
        with self.assertRaisesRegex(ValueError, "120000-frame cap"):
            instrument_private_eleventh_confirm_on_stage143(original.encode())

    def test_double_application_fails_closed(self):
        first = instrument_private_eleventh_confirm_on_stage143(fixture().encode())
        with self.assertRaisesRegex(ValueError, "already instrumented"):
            instrument_private_eleventh_confirm_on_stage143(first)

    def test_missing_tenth_confirm_anchor_fails_closed(self):
        original = fixture().replace(SETUP_CONFIRM10, "", 1)
        with self.assertRaisesRegex(ValueError, "tenth-C source anchors"):
            instrument_private_eleventh_confirm_on_stage143(original.encode())

    def test_event_count_mismatch_fails_closed(self):
        original = fixture().replace("PerPadCPressed(vh107_pad);\n", "", 1)
        with self.assertRaisesRegex(ValueError, "input event counts"):
            instrument_private_eleventh_confirm_on_stage143(original.encode())


if __name__ == "__main__":
    unittest.main()
