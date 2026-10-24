"""Stage144 eleventh-C schedule contract tests; no original media."""
import unittest

from tools.saturn_private_prologue_continue_eleventh_c_audit import (
    FRAME_COUNT, CONFIRM11_PRESS, CONFIRM11_RELEASE, CHECKPOINTS,
    PRE_ELEVENTH_CHECKPOINTS, POST_ELEVENTH_BY_121200,
    DECA_EVENTS_132, DECA_STATE_132, ELEVA_EVENTS, ELEVA_STATE,
)


class EleventhCReceiptScheduleTests(unittest.TestCase):
    def test_control_has_shared_tenth_c_and_132000_footer(self):
        self.assertEqual(FRAME_COUNT, 132000)
        self.assertIn(b"VH_PAD frame=108000 button=C action=PRESS\n", DECA_EVENTS_132)
        self.assertIn(b"VH_PAD frame=108006 button=C action=RELEASE\n", DECA_EVENTS_132)
        self.assertIn(b"VH_PAD mode=1 completed_frames=132000\n", DECA_EVENTS_132)
        self.assertNotIn(b"VH_PAD frame=120000 button=C action=PRESS\n", DECA_EVENTS_132)

    def test_intervention_adds_only_eleventh_c_receipts(self):
        self.assertEqual(CONFIRM11_PRESS, 120000)
        self.assertEqual(CONFIRM11_RELEASE, 120006)
        self.assertIn(b"VH_PAD frame=120000 button=C action=PRESS\n", ELEVA_EVENTS)
        self.assertIn(b"VH_PAD frame=120006 button=C action=RELEASE\n", ELEVA_EVENTS)
        self.assertIn(b"VH_PADSTATE frame=120000 button=C active_low_bit=0\n", ELEVA_STATE)
        self.assertIn(b"VH_PADSTATE frame=120006 button=C active_low_bit=1\n", ELEVA_STATE)
        self.assertNotIn(b"VH_PAD frame=120000 button=C action=PRESS\n", DECA_EVENTS_132)
        self.assertNotIn(b"VH_PADSTATE frame=120000 button=C active_low_bit=0\n", DECA_STATE_132)

    def test_checkpoint_window_is_999_pre_and_101_post(self):
        self.assertEqual(len(CHECKPOINTS), 1100)
        self.assertEqual(len(PRE_ELEVENTH_CHECKPOINTS), 999)
        self.assertEqual(PRE_ELEVENTH_CHECKPOINTS[-1], 119880)
        self.assertEqual(len(CHECKPOINTS) - len(PRE_ELEVENTH_CHECKPOINTS), 101)

    def test_early_divergence_window_begins_after_eleventh_press(self):
        self.assertEqual(POST_ELEVENTH_BY_121200[0], 120120)
        self.assertEqual(POST_ELEVENTH_BY_121200[-1], 121200)
        self.assertEqual(len(POST_ELEVENTH_BY_121200), 10)


if __name__ == "__main__":
    unittest.main()
