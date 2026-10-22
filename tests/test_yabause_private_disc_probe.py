"""Stage98 public-only exact original runner source and private probe contracts."""
import unittest

from tools.patch_yabause_private_disc_probe import (
    MODE, PASS, STAGE98_CONDITION, PROBE_CHECK, instrument_probe_runner,
)
from tools.verify_yabause_public_disc_probe import FAKE_FADS


class RealYabausePrivateDiscProbeContracts(unittest.TestCase):
    def test_original_runner_pin_still_fail_closed(self):
        for raw in (b"", b"fake" * 5000, b"int main() { return 0; }"):
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                instrument_probe_runner(raw)

    def test_probe_only_opt_in_and_exact_cue_argument(self):
        self.assertEqual(MODE, "vh-private-disc-probe")
        self.assertIn('strcmp(argv[1], "vh-private-disc-probe")', STAGE98_CONDITION)
        self.assertIn("argc == 3", STAGE98_CONDITION)
        self.assertIn("ISOCD.Init(argv[2])", PROBE_CHECK)
        self.assertIn("ISOCD.ReadTOC(toc)", PROBE_CHECK)
        self.assertIn("VH_SATURN_CAPTURE_GATE", PROBE_CHECK)
        self.assertIn("VH_SATURN_FAD_LOG", PROBE_CHECK)

    def test_physically_read_real_iso_cd_but_no_gameplay(self):
        for marker in (
            "ISOCD.ReadSectorFAD(150", "ISOCD.ReadSectorFAD(151",
            "ISOCD.ReadSectorFAD(166", "ISOCD.ReadSectorFAD(2479",
            "ISOCD.ReadSectorFAD(76486", "ISOCD.ReadSectorFAD(audio_start",
            'memcmp(sector + 16, "SEGA SEGASATURN", 15)',
            'memcmp(sector + 17, "CD001", 5)', "remove(gate_path)",
            "ISOCD.DeInit()", "YabauseDeInit()",
        ):
            self.assertIn(marker, PROBE_CHECK)
        self.assertIn(PASS, PROBE_CHECK)
        self.assertNotIn("fwrite(sector", PROBE_CHECK)
        self.assertNotIn("fwrite(buffer", PROBE_CHECK)
        self.assertNotIn("original_first_battle_verified=true", PROBE_CHECK)

    def test_known_stage02_candidate_fad_math_metadata_only(self):
        self.assertEqual(2329 + 150, 2479)
        self.assertEqual(76336 + 150, 76486)
        self.assertEqual(16 + 150, 166)
        self.assertEqual(150 + 264352 + 150, 264652)

    def test_invented_short_disc_log(self):
        self.assertEqual(
            FAKE_FADS, b"VHCD_FAD 150\nVHCD_FAD 151\nVHCD_FAD 302\n"
        )


if __name__ == "__main__":
    unittest.main()
