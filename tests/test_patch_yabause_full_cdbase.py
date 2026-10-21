"""Stage80: whole-file pinned-source patch must fail closed and avoid overwrite."""
import tempfile
from pathlib import Path
import unittest

from tools.patch_yabause_full_cdbase import patch_full_cdbase, create_patched_source


class FullSourcePatchTests(unittest.TestCase):
    def test_rejects_non_pinned_content(self):
        for data in (b"", b"pretend source", b"\x00" * 100_000, b"1" * 160_001):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                patch_full_cdbase(data)

    def test_rejects_wrong_source_file_name(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "some_other_file.c"
            path.write_bytes(b"x" * 1024)
            with self.assertRaises(ValueError):
                create_patched_source(path, root / "out.c")

    def test_never_overwrites_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "cdbase.c"
            source.write_bytes(b"not pinned" * 500)
            output = root / "instrumented.c"
            output.write_text("keep-me")
            with self.assertRaises(ValueError):
                create_patched_source(source, output)
            self.assertEqual(output.read_text(), "keep-me")

    def test_rejects_in_place_modification(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "cdbase.c"
            source.write_bytes(b"not pinned" * 500)
            with self.assertRaises(ValueError):
                create_patched_source(source, source)

    def test_invalid_source_never_creates_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "cdbase.c", root / "patched.c"
            source.write_bytes(b"not pinned" * 500)
            with self.assertRaises(ValueError):
                create_patched_source(source, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
