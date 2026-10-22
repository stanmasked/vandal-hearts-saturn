"""Stage97: only invented compressed bytes. No original Track1 in public CI."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.saturn_private_track1_splitzip_join import join_split_zip


class SplitZipPrivateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.parts_dir = self.root / "parts"
        self.parts_dir.mkdir(mode=0o700)
        self.dst_dir = self.root / "source"
        self.dst_dir.mkdir(mode=0o700)
        self.output = self.dst_dir / "invented-track1.bin"
        self.payload = bytes((j * 53 + (j // 2352)) % 256 for j in range(2352 * 28))
        self.pin = (len(self.payload), hashlib.sha256(self.payload).hexdigest())
        self.parts = self.make_parts(self.payload)

    def make_parts(self, payload: bytes, *, member="invented-track1.bin",
                   extra=False, compression=zipfile.ZIP_DEFLATED):
        archive = self.root / "tmp.zip"
        with zipfile.ZipFile(archive, "w", compression=compression) as z:
            z.writestr(member, payload)
            if extra:
                z.writestr("extra.bin", b"fake")
        blob = archive.read_bytes()
        archive.unlink()
        pieces = [blob[:len(blob) // 2], blob[len(blob) // 2:]]
        out = []
        for i, piece in enumerate(pieces, 1):
            path = self.parts_dir / ("invented-track1.bin.zip.%03d" % i)
            path.write_bytes(piece)
            path.chmod(0o600)
            out.append(path)
        return out

    def join(self, *, parts=None, output=None, pin=None):
        return join_split_zip(self.parts if parts is None else parts,
                              self.output if output is None else output,
                              expected=self.pin if pin is None else pin)

    def test_two_split_volumes_restore_original_bytes_and_sha(self):
        receipt = self.join()
        self.assertTrue(receipt["full_stage02_track1_sha256_verified"])
        self.assertTrue(receipt["zip_member_crc_validated"])
        self.assertEqual(receipt["split_volume_count"], 2)
        self.assertEqual(self.output.read_bytes(), self.payload)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o400)
        self.assertFalse(receipt["original_game_boot_verified"])
        self.assertEqual([p for p in self.dst_dir.iterdir()], [self.output])

    def test_reverse_cli_input_order_is_sorted_by_numeric_suffix(self):
        self.join(parts=list(reversed(self.parts)))
        self.assertEqual(self.output.read_bytes(), self.payload)

    def test_one_or_missing_volume_rejected(self):
        with self.assertRaises(ValueError):
            self.join(parts=self.parts[:1])
        missing_index = self.parts_dir / "invented-track1.bin.zip.003"
        self.parts[1].rename(missing_index)
        with self.assertRaises(ValueError):
            self.join(parts=[self.parts[0], missing_index])

    def test_bad_volume_mismatch_or_duplicate_rejected(self):
        other = self.parts_dir / "another.zip.002"
        self.parts[1].rename(other)
        with self.assertRaises(ValueError):
            self.join(parts=[self.parts[0], other])
        with self.assertRaises(ValueError):
            self.join(parts=[self.parts[0], self.parts[0]])

    def test_corrupt_split_volumes_rejected_without_final_file(self):
        p = self.parts[1]
        content = bytearray(p.read_bytes())
        content[len(content)//3] ^= 23
        p.write_bytes(content)
        with self.assertRaises((ValueError, zipfile.BadZipFile, OSError)):
            self.join()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.dst_dir.iterdir()))

    def test_wrong_expected_full_sha_rejected(self):
        with self.assertRaises(ValueError):
            self.join(pin=(len(self.payload), "0" * 64))
        self.assertFalse(self.output.exists())

    def test_unexpected_output_basename_rejected(self):
        with self.assertRaises(ValueError):
            self.join(output=self.dst_dir / "renamed-track1.bin")
        self.assertFalse(list(self.dst_dir.iterdir()))

    def test_archive_member_traversal_rejected(self):
        for p in self.parts: p.unlink()
        self.parts = self.make_parts(self.payload, member="../escape.bin")
        with self.assertRaises(ValueError):
            self.join()
        self.assertFalse(list(self.dst_dir.iterdir()))

    def test_multiple_zip_entries_rejected(self):
        for p in self.parts: p.unlink()
        self.parts = self.make_parts(self.payload, extra=True)
        with self.assertRaises(ValueError):
            self.join()

    def test_truncated_second_volume_rejected(self):
        p = self.parts[1]
        p.write_bytes(p.read_bytes()[:-30])
        with self.assertRaises((ValueError, zipfile.BadZipFile, OSError)):
            self.join()
        self.assertFalse(self.output.exists())

    def test_symlink_volume_rejected(self):
        source = self.parts[0]
        alias = self.parts_dir / "symlink.zip.001"
        source.rename(self.root / "backing")
        alias.symlink_to(self.root / "backing")
        with self.assertRaises(ValueError):
            self.join(parts=[alias, self.parts[1]])

    def test_existing_target_is_not_overwritten(self):
        self.output.write_bytes(b"keep")
        with self.assertRaises(ValueError):
            self.join()
        self.assertEqual(self.output.read_bytes(), b"keep")

    def test_world_readable_or_checkout_input_refused(self):
        self.parts_dir.chmod(0o755)
        with self.assertRaises(ValueError):
            self.join()
        self.parts_dir.chmod(0o700)
        (self.root / ".git").mkdir()
        with self.assertRaises(ValueError):
            self.join()

    def test_uncompressed_zip_stored_method_supported(self):
        for p in self.parts: p.unlink()
        self.parts = self.make_parts(self.payload, compression=zipfile.ZIP_STORED)
        self.join()
        self.assertEqual(self.output.read_bytes(), self.payload)


if __name__ == "__main__":
    unittest.main()
