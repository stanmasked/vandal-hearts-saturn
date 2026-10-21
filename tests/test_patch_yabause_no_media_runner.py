"""Stage82 synthetic, media-free tests for pinned Yabause runner instrumentation."""
import tempfile
from pathlib import Path
import unittest

from tools.patch_yabause_no_media_runner import (
    SUCCESS, INJECTION, instrument_runner, patch_runner,
)


class YabauseRunnerInitPatchTests(unittest.TestCase):
    def test_rejects_unverified_code(self):
        for source in (b"", b"int main(int argc, char *argv[])\n{\n",
                       b"not pinned"*4000, b"\x00"*30098):
            with self.subTest(n=len(source)), self.assertRaises(ValueError):
                instrument_runner(source)

    def test_injected_mode_is_no_media_and_bios_free(self):
        self.assertIn("CDCORE_DUMMY", INJECTION)
        self.assertIn("yinit.biospath = NULL;", INJECTION)
        self.assertIn("yinit.cdpath = NULL;", INJECTION)
        self.assertIn("yinit.skip_load = 1;", INJECTION)
        self.assertIn("YabauseInit(&yinit)", INJECTION)
        self.assertIn("YabauseDeInit()", INJECTION)
        self.assertIn(SUCCESS, INJECTION)
        self.assertNotIn("ISOCD", INJECTION)
        self.assertNotIn("VH_SATURN_FAD_LOG", INJECTION)

    def test_rejects_inplace_and_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "yui.cpp"
            source.write_bytes(b"wrong" * 7000)
            out = Path(d) / "instrumented.cpp"
            with self.assertRaises(ValueError):
                patch_runner(source, source)
            out.write_text("unchanged", encoding="utf-8")
            with self.assertRaises(ValueError):
                patch_runner(source, out)
            self.assertEqual(out.read_text(), "unchanged")

    def test_rejects_invalid_unpinned_source_without_output_creation(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "yui.cpp"
            source.write_bytes(b"wrong" * 7000)
            out = Path(d) / "instrumented.cpp"
            with self.assertRaises(ValueError):
                patch_runner(source, out)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
