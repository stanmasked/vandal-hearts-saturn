import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.disc_inventory import scan


class DiscInventoryTests(unittest.TestCase):
    def test_single_track_metadata_and_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = b"SYNTHETIC TRACK -- NO GAME DATA"
            (root / "sample.bin").write_bytes(payload)
            cue = root / "sample.cue"
            cue.write_text('FILE "sample.bin" BINARY\n  TRACK 01 MODE1/2352\n    INDEX 01 00:00:00\n')
            report = scan(cue)
            self.assertEqual(report["tracks"], [{"number": 1, "mode": "MODE1/2352", "file": "sample.bin"}])
            self.assertEqual(report["files"][0]["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(report["files"][0]["size_bytes"], len(payload))
            self.assertNotIn("SYNTHETIC", str(report))

    def test_rejects_parent_directory_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cue = root / "sample.cue"
            cue.write_text('FILE "../external.bin" BINARY\n  TRACK 01 MODE1/2352\n')
            with self.assertRaises(ValueError):
                scan(cue)

    def test_missing_track_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cue = root / "sample.cue"
            cue.write_text('FILE "missing.bin" BINARY\n  TRACK 01 MODE1/2352\n')
            with self.assertRaises(FileNotFoundError):
                scan(cue)


if __name__ == "__main__":
    unittest.main()
