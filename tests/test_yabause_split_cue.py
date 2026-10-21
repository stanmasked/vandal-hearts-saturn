"""Stage89 test of pinned source patch and invented two-file Saturn-shaped CUE."""
import tempfile
from pathlib import Path
import unittest

from tools.patch_yabause_split_cue import (
    patch_split_cue, C_SOURCE, INIT_REPLACE,
)
from tools.patch_yabause_two_track_runner import (
    MODE, RECEIPT, SPLIT_CHECK, STAGE89_CONDITION, instrument_split_runner,
)
from tools.verify_yabause_split_cue import (
    AUDIO, CUE, DATA, EXPECTED, make_split_fixture,
)


class Stage89SplitCueTests(unittest.TestCase):
    def test_rejects_arbitrary_nonpinned_core(self):
        for src in (b"", b"Yabause" * 2000, b"LoadBinCue" * 20000):
            with self.subTest(size=len(src)), self.assertRaises(ValueError):
                patch_split_cue(src)

    def test_rejects_arbitrary_nonpinned_runner(self):
        for src in (b"", b"runner" * 3000, b"\x00" * 30098):
            with self.subTest(size=len(src)), self.assertRaises(ValueError):
                instrument_split_runner(src)

    def test_pregap_audio_and_file_identity_contract(self):
        for key in ("audio_index00 != 0", "audio_index01 != 150",
                    'strcmp(names[0], names[1])', "file_count != 2",
                    "data_index != 0", "fp[0]", "fp[1]",
                    "session->track[1].file_id = 1",
                    "session->track[1].file_offset = 150U * 2352U",
                    "session->track[1].fad_start = audio_start",
                    "fclose(cue)"):
            self.assertIn(key, C_SOURCE)
        self.assertIn("VHIsSplitCue(iso_file)", INIT_REPLACE)
        self.assertIn("LoadBinCue(iso, iso_file)", INIT_REPLACE)

    def test_real_yabause_audio_fad_and_frame_contract(self):
        self.assertEqual(MODE, "vh-two-file-cue-read")
        self.assertIn(MODE, STAGE89_CONDITION)
        for item in ("ISOCD.ReadTOC(toc)", "302U",
                     "ISOCD.ReadSectorFAD(150",
                     "ISOCD.ReadSectorFAD(151",
                     "ISOCD.ReadSectorFAD(302",
                     "ISOCD.ReadSectorFAD(303",
                     "ISOCD.ReadSectorFAD(304",
                     "sector[0] != 77", "remove(gate_path)", RECEIPT):
            self.assertIn(item, SPLIT_CHECK)

    def test_source_is_tiny_invented_and_not_original(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest, pins = make_split_fixture(root)
            self.assertEqual({p.name for p in root.iterdir()}, {DATA, AUDIO, CUE})
            self.assertEqual(pins["track1"][0], 2*2352)
            self.assertEqual(pins["track2"][0], 152*2352)
            self.assertIn(b"FILE ", (root/CUE).read_bytes())
            self.assertIn(b"TRACK 02 AUDIO", (root/CUE).read_bytes())
            self.assertEqual((root/DATA).read_bytes()[:2], bytes([17,18]))
            audio=(root/AUDIO).read_bytes()
            self.assertEqual(audio[150*2352:150*2352+2], bytes([77,78]))
            self.assertEqual(audio[151*2352:151*2352+2], bytes([88,89]))
            self.assertEqual(EXPECTED, b"VHCD_FAD 150\nVHCD_FAD 151\nVHCD_FAD 302\nVHCD_FAD 303\n")
            self.assertEqual(manifest["schema_version"], 1)

    def test_prevent_reusing_fixture_directory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_split_fixture(root)
            with self.assertRaises(ValueError):
                make_split_fixture(root)


if __name__ == "__main__":
    unittest.main()
