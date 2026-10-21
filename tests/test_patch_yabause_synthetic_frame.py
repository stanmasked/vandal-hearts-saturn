"""Stage83 synthetic-only, fail-closed Yabause runner frame instrumenter tests."""
import tempfile
from pathlib import Path
import unittest

from tools.patch_yabause_synthetic_frame import (
    FRAME_CHECK, MODE, RECEIPT, instrument_frame_runner, patch_runner_file,
)


class PinnedSyntheticFrameTests(unittest.TestCase):
    def test_rejects_unpinned_binary_or_source(self):
        for raw in (b"", b"int main() {}", b"yabause" * 10000, b"\x00" * 30098):
            with self.subTest(length=len(raw)), self.assertRaises(ValueError):
                instrument_frame_runner(raw)

    def test_invented_sh2_loop_and_register_evidence_contract(self):
        self.assertEqual(MODE, "vh-synthetic-sh2-frame")
        for marker in ("0x06000000U", "0x7001", "0xAFFD", "0x0009",
                       "SH2SetRegisters(MSH2, &before)",
                       "SH2GetRegisters(MSH2, &after)",
                       "after.R[0] == 0", "YabauseEmulate()", RECEIPT):
            self.assertIn(marker, FRAME_CHECK)
        self.assertNotIn("ISOCD", FRAME_CHECK)
        self.assertNotIn("VH_SATURN_FAD_LOG", FRAME_CHECK)

    def test_rejects_overwrite_or_in_place_patch(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "yui.cpp"
            source.write_bytes(b"fake" * 10000)
            output = Path(td) / "yui.generated.cpp"
            with self.assertRaises(ValueError):
                patch_runner_file(source, source)
            output.write_text("preserve", encoding="utf-8")
            with self.assertRaises(ValueError):
                patch_runner_file(source, output)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve")

    def test_failure_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "yui.cpp"
            source.write_bytes(b"fake" * 10000)
            output = Path(td) / "yui.generated.cpp"
            with self.assertRaises(ValueError):
                patch_runner_file(source, output)
            self.assertFalse(output.exists())

if __name__ == "__main__":
    unittest.main()
