"""Stage106 fake-only public C68K original-title capture contract."""
import unittest
from tools.patch_yabause_original_title_12000 import (
    BEFORE, AFTER, instrument_original_title_12000,
)

class PublicPinnedOriginalTitleTests(unittest.TestCase):
    def test_invalid_upstream_never_patches(self):
        for raw in (b"",b"untrusted fake",b"int main(){}"):
            with self.subTest(length=len(raw)),self.assertRaises(ValueError):
                instrument_original_title_12000(raw)

    def test_only_bounded_game_mode_can_grow(self):
        self.assertEqual(BEFORE,"frames < 1 || frames > 10800 ||")
        self.assertEqual(AFTER,"frames < 1 || frames > 12000 ||")

    def test_true_yabause_c68k_synthetic_paths_remain_pinned(self):
        from tools.patch_yabause_private_c68k_experiment import NEW
        from tools.patch_yabause_private_long_frames import CHECKPOINT
        self.assertIn("M68KCORE_C68K",NEW)
        self.assertEqual(CHECKPOINT,"if (progress % 120 == 0)")

if __name__=="__main__":
    unittest.main()
