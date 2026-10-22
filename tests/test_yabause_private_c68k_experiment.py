"""Stage103 synthetic-only public pinned C68K vs DUMMY experiment contracts."""
import unittest
from tools.patch_yabause_private_c68k_experiment import (
    OLD,NEW,instrument_sound_cpu_runner
)

class SoundCpuSingleVariableExperiment(unittest.TestCase):
    def test_unpinned_upstream_always_rejected(self):
        for raw in (b"",b"fake",b"int main() {}"):
            with self.subTest(n=len(raw)),self.assertRaises(ValueError):
                instrument_sound_cpu_runner(raw)

    def test_only_optin_original_disc_mode_gets_c68k(self):
        self.assertIn("source_game.m68kcoretype",OLD)
        self.assertIn("source_game.m68kcoretype",NEW)
        self.assertIn("M68KCORE_DUMMY",OLD)
        self.assertIn("M68KCORE_C68K",NEW)
        self.assertNotEqual(OLD,NEW)

    def test_stage83_synthetic_sh2_and_dummy_audio_unchanged(self):
        self.assertNotIn("yinit.m68kcoretype",OLD)
        self.assertNotIn("source_game.sndcoretype",NEW)


if __name__=="__main__":
    unittest.main()
