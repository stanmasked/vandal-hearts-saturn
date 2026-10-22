"""Stage97: synthetic-only private ZIP splits under the raw Drive limit."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.saturn_private_track1_split_zip import (
    MANIFEST, split_private_track1, join_private_track1,
)


class SplitPrivateTrack1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.src = self.root / "invented-track1.bin"
        self.src.write_bytes(bytes((i * 37 + 5) & 255 for i in range(2352 * 10)))
        self.src.chmod(0o600)
        self.pins = (self.src.stat().st_size, hashlib.sha256(self.src.read_bytes()).hexdigest())
        self.archive = self.root / "chunks"
        self.archive.mkdir(mode=0o700)
        self.outdir = self.root / "assembled"
        self.outdir.mkdir(mode=0o700)
        self.output = self.outdir / self.src.name

    def split(self):
        return split_private_track1(
            self.src, self.archive, chunk_bytes=4096, expected=self.pins,
        )

    def join(self):
        return join_private_track1(self.archive, self.output, expected=self.pins)

    def test_split_then_reconstruct_byte_identical_with_readonly_result(self):
        report = self.split()
        self.assertEqual(report["zip_archives_created"], 6)
        self.assertTrue(report["all_archives_smaller_than_256_mib"])
        manifest = json.loads((self.archive / MANIFEST).read_text())
        self.assertEqual(len(manifest["parts"]), 6)
        self.assertEqual(manifest["track1_sha256"], self.pins[1])
        for i, part in enumerate(manifest["parts"]):
            path = self.archive / part["archive"]
            self.assertTrue(path.is_file())
            self.assertLess(path.stat().st_size, 256 * 1024 * 1024)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with zipfile.ZipFile(path) as z:
                self.assertEqual(z.namelist(), [f"track1-part-{i:03d}.raw"])
                self.assertEqual(z.infolist()[0].compress_type, zipfile.ZIP_STORED)
        result = self.join()
        self.assertTrue(result["full_stage02_track1_sha256_verified"])
        self.assertFalse(result["original_game_boot_verified"])
        self.assertEqual(self.output.read_bytes(), self.src.read_bytes())
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o400)
        self.assertEqual({p.name for p in self.outdir.iterdir()}, {self.output.name})

    def test_changed_member_archive_rejected_and_no_partial_output(self):
        self.split()
        file = self.archive / "track1-part-001.zip"
        with file.open("ab") as out:
            out.write(b"tamper")
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            self.join()
        self.assertEqual(list(self.outdir.iterdir()), [])

    def test_missing_archive_is_rejected(self):
        self.split()
        (self.archive / "track1-part-002.zip").unlink()
        with self.assertRaises(ValueError):
            self.join()
        self.assertFalse(self.output.exists())

    def test_wrong_complete_image_sha_refuses_split(self):
        with self.assertRaises(ValueError):
            split_private_track1(
                self.src, self.archive, chunk_bytes=4096,
                expected=(self.pins[0], "0" * 64),
            )
        self.assertEqual(list(self.archive.iterdir()), [])

    def test_invalid_source_size_refuses_split(self):
        with self.assertRaises(ValueError):
            split_private_track1(
                self.src, self.archive, chunk_bytes=4096,
                expected=(self.pins[0] + 2352, self.pins[1]),
            )
        self.assertEqual(list(self.archive.iterdir()), [])

    def test_extra_file_rejected_and_archive_not_deleted(self):
        self.split()
        (self.archive / "unrelated.txt").write_text("fake")
        with self.assertRaises(ValueError):
            self.join()
        self.assertTrue((self.archive / "track1-part-000.zip").exists())

    def test_manifest_reorder_and_path_traversal_rejected(self):
        self.split()
        file = self.archive / MANIFEST
        original = file.read_bytes()
        manifest = json.loads(original)
        manifest["parts"][0]["archive"] = "../unsafe.zip"
        file.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            self.join()
        file.write_bytes(original)
        manifest = json.loads(original)
        manifest["parts"][0], manifest["parts"][1] = (
            manifest["parts"][1], manifest["parts"][0]
        )
        file.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            self.join()

    def test_duplicate_output_never_overwritten(self):
        self.split()
        self.output.write_bytes(b"keep existing original")
        with self.assertRaises(ValueError):
            self.join()
        self.assertEqual(self.output.read_bytes(), b"keep existing original")

    def test_symlink_or_hardlink_source_rejected(self):
        alias = self.root / "linked.bin"
        alias.symlink_to(self.src)
        with self.assertRaises(ValueError):
            split_private_track1(alias, self.archive, chunk_bytes=4096,
                                 expected=self.pins)
        os.link(self.src, self.root / "hardlink.bin")
        with self.assertRaises(ValueError):
            self.split()
        self.assertEqual(list(self.archive.iterdir()), [])

    def test_nonprivate_folder_and_inside_checkout_rejected(self):
        self.archive.chmod(0o755)
        with self.assertRaises(ValueError):
            self.split()
        self.archive.chmod(0o700)
        (self.root / ".git").mkdir()
        with self.assertRaises(ValueError):
            self.split()

    def test_wrong_final_digest_prevents_output_without_moving_chunks(self):
        self.split()
        altered = (self.pins[0], "f" * 64)
        with self.assertRaises(ValueError):
            join_private_track1(self.archive, self.output, expected=altered)
        self.assertEqual(list(self.outdir.iterdir()), [])
        self.assertTrue((self.archive / MANIFEST).exists())

    def test_invalid_chunk_size_rejected(self):
        for size in (0, 1024, -1, True, 161 * 1024 * 1024):
            with self.subTest(size=size), self.assertRaises(ValueError):
                split_private_track1(
                    self.src, self.archive, chunk_bytes=size,
                    expected=self.pins,
                )
        self.assertEqual(list(self.archive.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
