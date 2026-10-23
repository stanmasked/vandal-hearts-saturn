"""Stage126 private packager: invented-only raw inputs and no disc media."""
import hashlib
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest
import zlib

from tools.saturn_private_capture_packager import package_stage124_style_pair
from tools.saturn_private_capture_archive_gate import (
    SIDECARS, verify_private_stage124_archive,
)


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)


PNG = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0))
       + _chunk(b"IDAT", zlib.compress(b"".join(b"\0"+bytes(64*3) for _ in range(64))))
       + _chunk(b"IEND", b""))


def _make_synthetic_pair(root: Path, *, checkpoints: int = 2):
    control, enabled = root / "control", root / "enabled"
    for folder in (control, enabled):
        folder.mkdir(mode=0o700)
        for frame in range(120, 120 * (checkpoints+1), 120):
            (folder / f"frame-{frame}.png").write_bytes(PNG)
        for name in SIDECARS:
            (folder / name).write_bytes(PNG if name.endswith(".png") else b"INVENTED-ONLY-DIAGNOSTICS")
    return control, enabled


class SyntheticPrivateCapturePackagingTests(unittest.TestCase):
    def test_package_and_verify_only_local_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            a, b = _make_synthetic_pair(folder)
            output = folder / "fresh-recapture.tar.gz"
            result = package_stage124_style_pair(a, b, output, checkpoints=2)
            self.assertTrue(result["archive_matches_supplied_fingerprint"])
            self.assertFalse(result["drive_upload_and_readback_verified"])
            self.assertFalse(result["historical_stage124_archive_recovered"])
            self.assertEqual(result["checkpoint_pngs"], 4)
            self.assertEqual(result["regular_members"], 20)
            with tarfile.open(output, "r:gz") as tar:
                self.assertEqual(len(tar.getmembers()), 20)
                self.assertTrue(all(m.isfile() and m.name.startswith("stage124-recapture/")
                                    for m in tar.getmembers()))
            self.assertEqual(result["archive_bytes"], output.stat().st_size)
            self.assertEqual(len(hashlib.sha256(output.read_bytes()).hexdigest()), 64)
            self.assertEqual({p.name for p in a.iterdir()},
                             {f"frame-{n}.png" for n in (120, 240)} | SIDECARS)

    def test_rejects_missing_capture_preserving_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            a, b = _make_synthetic_pair(folder)
            (b / "video-state.txt").unlink()
            output = folder / "bad.tar.gz"
            with self.assertRaisesRegex(ValueError, "incomplete"):
                package_stage124_style_pair(a, b, output, checkpoints=2)
            self.assertFalse(output.exists())
            self.assertTrue((a / "frame-120.png").exists())

    def test_rejects_symlink_and_hardlink_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            a, b = _make_synthetic_pair(folder)
            link = b / "frame-120.png"
            link.unlink()
            link.symlink_to(a / "frame-120.png")
            with self.assertRaises(ValueError):
                package_stage124_style_pair(a, b, folder / "bad.tar.gz", checkpoints=2)
            link.unlink()
            import os
            os.link(a / "frame-120.png", link)
            with self.assertRaises(ValueError):
                package_stage124_style_pair(a, b, folder / "bad.tar.gz", checkpoints=2)

    def test_existing_output_and_overlapping_paths_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            a, b = _make_synthetic_pair(folder)
            output = folder / "keep-me.tar.gz"
            output.write_bytes(b"DO-NOT-TOUCH")
            with self.assertRaises(ValueError):
                package_stage124_style_pair(a, b, output, checkpoints=2)
            self.assertEqual(output.read_bytes(), b"DO-NOT-TOUCH")
            with self.assertRaises(ValueError):
                package_stage124_style_pair(a, a, folder / "new.tar.gz", checkpoints=2)
            self.assertFalse((folder / "new.tar.gz").exists())

    def test_rejects_invalid_checkpoint_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            a, b = _make_synthetic_pair(folder)
            for count in (0, 901, True):
                with self.subTest(count=count):
                    with self.assertRaises(ValueError):
                        package_stage124_style_pair(a, b, folder / "bad.tar.gz", checkpoints=count)
            self.assertFalse((folder / "bad.tar.gz").exists())


if __name__ == "__main__":
    unittest.main()
