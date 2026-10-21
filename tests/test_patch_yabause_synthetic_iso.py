"""Stage84: verify generated host ISO callback test stays entirely synthetic."""
import tempfile
from pathlib import Path
import unittest

from tools.patch_yabause_synthetic_iso import (
    MODE, RECEIPT, CD_CHECK, NEW_CONDITION, instrument_cd_runner,
    patch_runner_file,
)


class PinnedLiveIsoTests(unittest.TestCase):
    def test_rejects_unpinned_runner(self):
        for source in (b"", b"fake-yabause" * 5000, b"\0" * 30098):
            with self.subTest(n=len(source)), self.assertRaises(ValueError):
                instrument_cd_runner(source)

    def test_genuine_iso_interface_is_covered_without_game(self):
        self.assertEqual(MODE, "vh-synthetic-iso-read")
        self.assertIn(MODE, NEW_CONDITION)
        for v in ("ISOCD.Init(", "ISOCD.DeInit()", "ISOCD.ReadSectorFAD(150",
                  "ISOCD.ReadSectorFAD(151", "ISOCD.ReadSectorFAD(152",
                  'fputs("1\\n", gate)', 'fputs("1\\r\\n", gate)',
                  "sector[16] != 7", "sector[16] != 40",
                  "YabauseDeInit()", RECEIPT):
            self.assertIn(v, CD_CHECK)
        self.assertNotIn("Vandal", CD_CHECK)
        self.assertNotIn("original_assets", CD_CHECK)

    def test_wrong_source_creates_no_output(self):
        with tempfile.TemporaryDirectory() as td:
            source, dest = Path(td) / "yui.cpp", Path(td) / "generated.cpp"
            source.write_bytes(b"fake" * 15000)
            with self.assertRaises(ValueError):
                patch_runner_file(source, dest)
            self.assertFalse(dest.exists())

    def test_no_inplace_or_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            src, dst = Path(td) / "yui.cpp", Path(td) / "generated.cpp"
            src.write_bytes(b"invalid" * 5000)
            with self.assertRaises(ValueError):
                patch_runner_file(src, src)
            dst.write_text("unchanged")
            with self.assertRaises(ValueError):
                patch_runner_file(src, dst)
            self.assertEqual(dst.read_text(), "unchanged")

if __name__ == "__main__":
    unittest.main()
