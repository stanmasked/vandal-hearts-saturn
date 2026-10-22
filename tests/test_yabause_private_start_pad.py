"""Stage107: fake-only test of original title START pad wiring."""
import unittest
from tools.patch_yabause_private_start_pad import (
    BEFORE, AFTER, SETUP, CONNECT, LOOP, FINALIZE, instrument_gamepad_start,
)

class GenuineSaturnPadStartContracts(unittest.TestCase):
    def test_bad_unpinned_source_rejected(self):
        for raw in (b"", b"tampered", b"int main(){}"):
            with self.subTest(size=len(raw)),self.assertRaises(ValueError):
                instrument_gamepad_start(raw)

    def test_both_runs_use_same_controller(self):
        self.assertIn("PerPadAdd(&PORTDATA1)",CONNECT)
        self.assertIn("if (!vh107_pad)",CONNECT)
        self.assertIn("vh107_start_at >= 0",LOOP)
        self.assertIn("PerPadStartPressed(vh107_pad)",LOOP)
        self.assertIn("PerPadStartReleased(vh107_pad)",LOOP)

    def test_exact_six_frame_press_with_after_title_gate(self):
        self.assertIn('getenv("VH_SATURN_START_AT_FRAME")',SETUP)
        self.assertIn("n < 12000L",SETUP)
        self.assertIn("n > (long)frames - 8L",SETUP)
        self.assertIn("frame == vh107_start_at + 6",LOOP)
        self.assertEqual(BEFORE,"frames < 1 || frames > 12000 ||")
        self.assertEqual(AFTER,"frames < 1 || frames > 13200 ||")

    def test_local_numeric_events_not_original_assets(self):
        for value in (
            "VH_PAD frame=%d button=START action=PRESS",
            "VH_PAD frame=%d button=START action=RELEASE",
        ):self.assertIn(value,LOOP)
        self.assertIn("VH_PAD mode=%d completed_frames=%d",FINALIZE)
        self.assertNotIn("fwrite(",LOOP)
        self.assertNotIn("screenshot",LOOP)


if __name__=="__main__":
    unittest.main()
