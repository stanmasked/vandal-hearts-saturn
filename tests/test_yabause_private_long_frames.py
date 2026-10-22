"""Stage104: ensure extended C68K frame mode stays private and bounded."""
import unittest

from tools.patch_yabause_private_long_frames import (
    CHECKPOINT, GAME_MODE, NEW, OLD, instrument_extended_c68k_frames,
)


class ExtendedOriginalSaturnFrameTests(unittest.TestCase):
    def test_unpinned_upstream_is_rejected(self):
        for source in (b"", b"fake", b"int main(void) {return 0;}"):
            with self.subTest(size=len(source)), self.assertRaises(ValueError):
                instrument_extended_c68k_frames(source)

    def test_bounded_frame_count_and_120_frame_checkpoints(self):
        self.assertEqual(OLD, "frames < 1 || frames > 600 ||")
        self.assertEqual(NEW, "frames < 1 || frames > 3600 ||")
        self.assertEqual(CHECKPOINT, "if (progress % 120 == 0)")
        self.assertIn("vh-private-frame-boot", GAME_MODE)

    def test_core_remains_genuine_and_not_synthetic_dummy(self):
        from tools.patch_yabause_private_c68k_experiment import NEW as CPU
        self.assertEqual(CPU, "         source_game.m68kcoretype = M68KCORE_C68K;")
        self.assertNotIn("M68KCORE_DUMMY", CPU)

    def test_no_media_payloads_in_public_instrumenter(self):
        from tools import patch_yabause_private_long_frames as stage
        code = stage.__doc__ + stage.instrument_extended_c68k_frames.__doc__ if stage.instrument_extended_c68k_frames.__doc__ else stage.__doc__
        self.assertIn("No copyrighted game data", code)


if __name__ == "__main__":
    unittest.main()
