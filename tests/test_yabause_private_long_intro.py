"""Stage105 invented-only long-run cap contracts; no copyrighted disc required."""
import unittest
from tools.patch_yabause_private_long_intro import OLD, NEW, instrument_long_intro

class PrivateSaturnLongIntroTests(unittest.TestCase):
    def test_only_original_pinned_public_runner_accepted(self):
        for raw in (b"",b"invalid",b"main() {}"):
            with self.subTest(size=len(raw)),self.assertRaises(ValueError):
                instrument_long_intro(raw)

    def test_one_parameter_frame_limit_and_no_implicit_input(self):
        self.assertIn("frames > 3600",OLD)
        self.assertIn("frames > 9000",NEW)
        self.assertIn("frames < 1",NEW)
        self.assertNotIn("start_pressed",NEW)

    def test_frame_clock_remains_private(self):
        self.assertNotIn("original_game_media",NEW)
        self.assertNotIn("first_battle_verified",NEW)


if __name__=="__main__":
    unittest.main()
