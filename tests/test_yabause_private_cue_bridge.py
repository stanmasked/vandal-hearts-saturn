"""Stage88 public-only generated CUE/BIN and pinned upstream source protections."""
import tempfile
from pathlib import Path
import unittest

from tools.patch_yabause_real_cue import (
    MODE, RECEIPT, STAGE88_CONDITION, CUE_CHECK, instrument_runner,
)
from tools.verify_yabause_private_cue_bridge import (
    CUE_NAME, GOOD_LOG, TRACK1_NAME, TRACK2_NAME, make_fake_disc,
)


class Stage88PublicCueTests(unittest.TestCase):
    def test_rejects_unpinned_runner(self):
        for data in (b"", b"fake" * 10000, b"\x00" * 30098):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                instrument_runner(data)

    def test_synthetic_cue_fixture_is_small_and_self_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, pins = make_fake_disc(root)
            self.assertEqual(set(manifest["files"]), {"track1", "track2", "cue"})
            self.assertEqual(
                {p.name for p in root.iterdir()},
                {TRACK1_NAME, TRACK2_NAME, CUE_NAME},
            )
            self.assertEqual(pins["track1"][0], 4704)
            data = (root / TRACK1_NAME).read_bytes()
            self.assertEqual(data[:2], bytes([17, 18]))
            self.assertEqual(data[2352:2354], bytes([50, 51]))
            cue = (root / CUE_NAME).read_text()
            self.assertIn('TRACK 01 MODE1/2352', cue)
            self.assertIn('INDEX 01 00:00:00', cue)
            self.assertIn(TRACK1_NAME, cue)

    def test_refuses_reuse_of_nonempty_disc_source_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            make_fake_disc(directory)
            with self.assertRaises(ValueError):
                make_fake_disc(directory)

    def test_exact_cue_argv_and_read_evidence_contract(self):
        self.assertEqual(MODE, "vh-exact-cue-read")
        self.assertIn('argc == 3', STAGE88_CONDITION)
        self.assertIn("ISOCD.Init(argv[2])", CUE_CHECK)
        self.assertIn("ISOCD.ReadSectorFAD(150", CUE_CHECK)
        self.assertIn("ISOCD.ReadSectorFAD(151", CUE_CHECK)
        self.assertIn("ISOCD.ReadSectorFAD(152", CUE_CHECK)
        self.assertIn("remove(gate_path)", CUE_CHECK)
        self.assertIn(RECEIPT, CUE_CHECK)
        self.assertNotIn("Vandal Hearts", CUE_CHECK)
        self.assertEqual(GOOD_LOG, b"VHCD_FAD 150\nVHCD_FAD 151\n")


if __name__ == "__main__":
    unittest.main()
