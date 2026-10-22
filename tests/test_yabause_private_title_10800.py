"""Stage105 public-only regression of capped original Saturn C68K intro run."""
import unittest
from tools.patch_yabause_private_title_10800 import (
    BEFORE, AFTER, instrument_title_long_run,
)

class PrivateOriginalIntroLongRun(unittest.TestCase):
    def test_only_pinned_public_yabause_is_instrumentable(self):
        for raw in (b"", b"not-upstream", b"int main(){}"):
            with self.subTest(raw_size=len(raw)), self.assertRaises(ValueError):
                instrument_title_long_run(raw)

    def test_only_frame_limit_changes(self):
        self.assertEqual(BEFORE,"frames < 1 || frames > 3600 ||")
        self.assertEqual(AFTER,"frames < 1 || frames > 10800 ||")
        self.assertNotEqual(BEFORE,AFTER)

    def test_c68k_and_120_step_checkpoints_are_inherited(self):
        from tools.patch_yabause_private_c68k_experiment import NEW
        from tools.patch_yabause_private_long_frames import CHECKPOINT
        self.assertIn("M68KCORE_C68K", NEW)
        self.assertEqual(CHECKPOINT,"if (progress % 120 == 0)")


if __name__=="__main__":
    unittest.main()
