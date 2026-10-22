"""Stage104: invented-only contracts for long original-disc private emulator window."""
import unittest
from tools.patch_yabause_private_title_progress import (
    OLD,NEW,instrument_title_progress
)


class PrivateSaturnTitleProgressTests(unittest.TestCase):
    def test_unpinned_source_rejected(self):
        for raw in (b"",b"strange",b"int main(){}"):
            with self.subTest(size=len(raw)),self.assertRaises(ValueError):
                instrument_title_progress(raw)

    def test_only_private_window_is_extended(self):
        self.assertIn("frames > 600",OLD)
        self.assertIn("frames > 3600",NEW)
        self.assertIn("frames < 1",NEW)

    def test_public_source_emulates_original_c68k_without_game_media(self):
        self.assertNotIn("TRACK1",NEW)
        self.assertNotIn("first_battle_verified",NEW)


if __name__=="__main__":
    unittest.main()
