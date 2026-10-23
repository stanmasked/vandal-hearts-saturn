"""Stage127 invented-only rclone roundtrip tests, with no network or Drive account."""
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tools.saturn_private_drive_roundtrip import private_archive_roundtrip
from test_saturn_private_capture_archive_gate import archive_at

REMOTE = "privateowner:VH-Saturn/Private Archives/Stage124-Captures/synthetic.tar.gz"


class PrivateRemoteRoundtripTests(unittest.TestCase):
    def _inputs(self, folder: Path):
        archive = folder / "invented-stage124.tar.gz"
        size, digest = archive_at(archive, count=2)
        download_dir = folder / "private-download"
        download_dir.mkdir(mode=0o700)
        return archive, size, digest, download_dir / "readback.tar.gz"

    def _invoke(self, archive, size, digest, download, **kwargs):
        return private_archive_roundtrip(archive, REMOTE, download, expected_size=size,
                                         expected_sha256=digest, rclone="python3", **kwargs)

    def test_local_upload_then_distinct_readback_matches_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source, size, digest, readback = self._inputs(folder)
            remote_bytes = folder / "invented-private-remote-copy"
            def fake_transfer(_executable, inp, out, *, ignore_existing):
                if ignore_existing:
                    self.assertEqual(inp, str(source))
                    self.assertEqual(out, REMOTE)
                    shutil.copyfile(source, remote_bytes)
                else:
                    self.assertEqual(inp, REMOTE)
                    self.assertEqual(out, str(readback))
                    shutil.copyfile(remote_bytes, readback)
            with patch("tools.saturn_private_drive_roundtrip._transfer", side_effect=fake_transfer) as mock:
                report = self._invoke(source, size, digest, readback)
                self.assertEqual(mock.call_count, 2)
            self.assertTrue(report["configured_remote_roundtrip_verified"])
            self.assertFalse(report["google_drive_owner_only_verified"])
            self.assertFalse(report["stage125_drive_receipt_issued"])
            self.assertFalse(report["historical_stage124_archive_recovered"])
            self.assertEqual(source.read_bytes(), readback.read_bytes())
            self.assertNotEqual(source.stat().st_ino, readback.stat().st_ino)

    def test_missing_archive_never_calls_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source, size, digest, readback = self._inputs(folder)
            source.unlink()
            with patch("tools.saturn_private_drive_roundtrip._transfer") as transfer:
                with self.assertRaises(ValueError):
                    self._invoke(source, size, digest, readback)
                transfer.assert_not_called()
            self.assertFalse(readback.exists())

    def test_wrong_source_digest_does_not_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source, size, digest, readback = self._inputs(folder)
            with patch("tools.saturn_private_drive_roundtrip._transfer") as transfer:
                with self.assertRaises(ValueError):
                    self._invoke(source, size, "f" * 64, readback)
                transfer.assert_not_called()
            self.assertTrue(source.exists())
            self.assertFalse(readback.exists())

    def test_corrupt_download_rejected_and_only_download_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source, size, digest, readback = self._inputs(folder)
            def fake_transfer(_executable, inp, out, *, ignore_existing):
                if not ignore_existing:
                    readback.write_bytes(b"NOT-AN-ARCHIVE")
            with patch("tools.saturn_private_drive_roundtrip._transfer", side_effect=fake_transfer):
                with self.assertRaisesRegex(ValueError, "readback checksum"):
                    self._invoke(source, size, digest, readback)
            self.assertFalse(readback.exists())
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), digest)

    def test_failed_upload_does_not_touch_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source, size, digest, readback = self._inputs(folder)
            with patch("tools.saturn_private_drive_roundtrip._transfer",
                       side_effect=ValueError("private upload rejected")):
                with self.assertRaises(ValueError):
                    self._invoke(source, size, digest, readback)
            self.assertTrue(source.exists())
            self.assertFalse(readback.exists())

    def test_existing_download_and_symlink_must_not_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source, size, digest, readback = self._inputs(folder)
            readback.write_bytes(b"KEEP-ME")
            with patch("tools.saturn_private_drive_roundtrip._transfer") as transfer:
                with self.assertRaises(ValueError):
                    self._invoke(source, size, digest, readback)
                transfer.assert_not_called()
            self.assertEqual(readback.read_bytes(), b"KEEP-ME")
            readback.unlink()
            readback.symlink_to(source)
            with self.assertRaises(ValueError):
                self._invoke(source, size, digest, readback)
            self.assertTrue(source.is_file())

    def test_remote_syntax_and_private_directory_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source, size, digest, readback = self._inputs(folder)
            for remote in ("", "https://example.com/x", "owner:../escape",
                           "owner:/root", "owner:a\nb", "owner:a//b", "owner:"):
                with self.subTest(remote=remote):
                    with self.assertRaises(ValueError):
                        private_archive_roundtrip(source, remote, readback,
                                                  expected_size=size,
                                                  expected_sha256=digest, rclone="python3")
            readback.parent.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "private directory"):
                self._invoke(source, size, digest, readback)
            self.assertFalse(readback.exists())


if __name__ == "__main__":
    unittest.main()
