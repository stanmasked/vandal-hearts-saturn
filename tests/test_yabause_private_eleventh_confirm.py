"""Synthetic-only Stage144 source-transform tests; no original disc media."""
import unittest
from unittest.mock import patch

from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_tenth_confirm import SETUP_CONFIRM10, CONFIRM10_PRESS, CONFIRM10_RELEASE
from tools.patch_yabause_private_durable_pad_receipts import PAD_OPEN, STATE_OPEN, PAD_UNBUFFERED, STATE_UNBUFFERED
from tools.patch_yabause_private_eleventh_confirm import (
    SETUP_CONFIRM11, CONFIRM11_PRESS, CONFIRM11_RELEASE,
    instrument_eleventh_confirm_on_stage143, instrument_full_private_eleventh_confirm,
)


def synthetic_stage143():
    mode = MODE_START + "\nframes > 120000\n" + SETUP_CONFIRM10
    mode += PAD_OPEN + PAD_UNBUFFERED + '         fprintf(vh107_pad_log, "START\\n");\n'
    mode += STATE_OPEN + STATE_UNBUFFERED + '         fprintf(vh109_state_log, "INITIAL\\n");\n'
    for _ in range(9):
        mode += (
            '         PerPadCPressed(vh107_pad);\n'
            '         fprintf(vh107_pad_log, "VH_PAD frame=%d button=%c action=PRESS\\n", frame, \\'C\\');\n'
            '         fprintf(vh109_state_log, "VH_PADSTATE frame=%d button=%c active_low_bit=0\\n", frame, \\'C\\');\n'
            '         PerPadCReleased(vh107_pad);\n'
            '         fprintf(vh107_pad_log, "VH_PAD frame=%d button=%c action=RELEASE\\n", frame, \\'C\\');\n'
            '         fprintf(vh109_state_log, "VH_PADSTATE frame=%d button=%c active_low_bit=1\\n", frame, \\'C\\');\n'
        )
    mode += CONFIRM10_PRESS + CONFIRM10_RELEASE + EMULATE_START + " return 0;\n" + MODE_END
    return ("OUTSIDE_PREFIX\n" + mode + "\nOUTSIDE_SUFFIX\nvh101_snapshot();\nvh102_snapshot();\n").encode()


class EleventhConfirmTests(unittest.TestCase):
    def test_adds_guarded_eleventh_c_and_144k_cap(self):
        result = instrument_eleventh_confirm_on_stage143(synthetic_stage143()).decode()
        self.assertEqual(result.count("frames > 144000"), 1)
        self.assertNotIn("frames > 120000", result)
        self.assertEqual(result.count("PerPadCPressed(vh107_pad);"), 11)
        self.assertEqual(result.count("PerPadCReleased(vh107_pad);"), 11)
        self.assertIn("VH_SATURN_CONFIRM_AT_FRAME11", result)
        self.assertIn("VH_SATURN_CONFIRM11_ENABLED", result)
        self.assertIn("vh125_confirm10_enabled != 1", SETUP_CONFIRM11)
        self.assertIn("frame == vh144_confirm_at11 + 6", result)

    def test_press_and_release_receipts_are_added_once(self):
        result = instrument_eleventh_confirm_on_stage143(synthetic_stage143()).decode()
        self.assertEqual(result.count('VH_PAD frame=%d button=%c action=PRESS'), 11)
        self.assertEqual(result.count('VH_PAD frame=%d button=%c action=RELEASE'), 11)
        self.assertEqual(result.count('VH_PADSTATE frame=%d button=%c active_low_bit=0'), 11)
        self.assertEqual(result.count('VH_PADSTATE frame=%d button=%c active_low_bit=1'), 11)
        self.assertEqual(result.count("setvbuf(vh107_pad_log, NULL, _IONBF, 0)"), 1)
        self.assertEqual(result.count("setvbuf(vh109_state_log, NULL, _IONBF, 0)"), 1)

    def test_source_outside_private_branch_is_unchanged(self):
        source = synthetic_stage143().decode()
        result = instrument_eleventh_confirm_on_stage143(source.encode()).decode()
        self.assertTrue(result.startswith("OUTSIDE_PREFIX\n"))
        self.assertTrue(result.endswith("\nOUTSIDE_SUFFIX\nvh101_snapshot();\nvh102_snapshot();\n"))

    def test_requires_exact_prior_tenth_c_setup(self):
        source = synthetic_stage143().decode().replace("vh125_confirm10_enabled", "broken_enabled", 1)
        with self.assertRaisesRegex(ValueError, "tenth-confirm source anchors"):
            instrument_eleventh_confirm_on_stage143(source.encode())

    def test_wrong_frame_cap_fails_closed(self):
        source = synthetic_stage143().replace(b"frames > 120000", b"frames > 108000")
        with self.assertRaisesRegex(ValueError, "120,000-frame cap"):
            instrument_eleventh_confirm_on_stage143(source)

    def test_double_application_fails_closed(self):
        first = instrument_eleventh_confirm_on_stage143(synthetic_stage143())
        with self.assertRaisesRegex(ValueError, "already instrumented"):
            instrument_eleventh_confirm_on_stage143(first)

    def test_wrong_tenth_c_count_fails_closed(self):
        source = synthetic_stage143().replace(b"PerPadCPressed(vh107_pad);", b"", 1)
        with self.assertRaisesRegex(ValueError, "ten-C receipt contract"):
            instrument_eleventh_confirm_on_stage143(source)

    def test_full_composition_runs_stage143_then_stage144(self):
        fixture = synthetic_stage143()
        with patch(
            "tools.patch_yabause_private_eleventh_confirm.instrument_full_private_durable_pad_receipts",
            return_value=fixture,
        ) as stage143:
            result = instrument_full_private_eleventh_confirm(b"pinned upstream")
        stage143.assert_called_once_with(b"pinned upstream")
        self.assertIn(b"VH_SATURN_CONFIRM_AT_FRAME11", result)
        self.assertIn(b"frames > 144000", result)
        self.assertEqual(result.count(b"PerPadCPressed(vh107_pad);"), 11)


if __name__ == "__main__":
    unittest.main()
