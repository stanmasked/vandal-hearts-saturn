"""Stage126 synthetic-only archive gate tests: absolutely no original media."""
import hashlib
from io import BytesIO
from pathlib import Path
import tarfile
import tempfile
import unittest

from tools.saturn_private_capture_archive_gate import verify_private_stage124_archive

PNG = b"\x89PNG\r\n\x1a\n" + b"SYNTHETIC-FRAME-ONLY"


def archive_at(path: Path, *, count: int = 2, omit: tuple[str, int] | None = None,
               traversal: bool = False, symlink: bool = False, invalid_png: bool = False,
               omit_sidecar: tuple[str, str] | None = None):
    with tarfile.open(path, "w:gz") as tar:
        for group in ("control", "enabled"):
            for n in range(120, 120 * (count + 1), 120):
                if omit == (group, n):
                    continue
                data = b"BADPNG" if invalid_png and group == "enabled" and n == 120 else PNG
                ent = tarfile.TarInfo(f"capture/{group}/frame-{n}.png")
                ent.size = len(data)
                tar.addfile(ent, BytesIO(data))
            for name in ("pre.png", "post.png", "frames.stats", "fad.vhcdlog",
                         "pad-events.txt", "pad-state.txt", "sh2-window.txt", "video-state.txt"):
                if omit_sidecar == (group, name):
                    continue
                data = PNG if name.endswith(".png") else b"SYNTHETIC-SIDECAR"
                ent = tarfile.TarInfo(f"capture/{group}/{name}")
                ent.size = len(data)
                tar.addfile(ent, BytesIO(data))
        if traversal:
            ent = tarfile.TarInfo("../escape.txt")
            ent.size = 1
            tar.addfile(ent, BytesIO(b"X"))
        if symlink:
            ent = tarfile.TarInfo("capture/alias")
            ent.type = tarfile.SYMTYPE
            ent.linkname = "elsewhere"
            tar.addfile(ent)
    return path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()


class PrivateArchiveGateTests(unittest.TestCase):
    def test_synthetic_cohorts_validate_without_drive_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic-stage124.tar.gz"
            size, digest = archive_at(path)
            result = verify_private_stage124_archive(path, expected_size=size,
                                                    expected_sha256=digest, checkpoints=2)
            self.assertEqual(result["checkpoint_pngs"], 4)
            self.assertEqual(result["regular_members"], 20)
            self.assertFalse(result["drive_upload_and_readback_verified"])

    def test_full_stage124_checkpoint_shape_is_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic-complete.tar.gz"
            size, digest = archive_at(path, count=900)
            result = verify_private_stage124_archive(path, expected_size=size,
                                                    expected_sha256=digest)
            self.assertEqual(result["checkpoint_pngs"], 1800)
            self.assertEqual(result["regular_members"], 1816)

    def test_corrupted_gzip_tail_rejected_even_if_digest_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic.tar.gz"
            archive_at(path)
            contents = bytearray(path.read_bytes())
            contents[-6] ^= 0xFF
            path.write_bytes(contents)
            size, digest = len(contents), hashlib.sha256(contents).hexdigest()
            with self.assertRaises(ValueError):
                verify_private_stage124_archive(path, expected_size=size,
                                                expected_sha256=digest, checkpoints=2)

    def test_wrong_digest_size_or_mutated_archive_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic.tar.gz"
            size, digest = archive_at(path)
            for bad in ((size + 1, digest), (size, "f" * 64)):
                with self.assertRaises(ValueError):
                    verify_private_stage124_archive(path, expected_size=bad[0],
                                                    expected_sha256=bad[1], checkpoints=2)
            with path.open("ab") as f:
                f.write(b"MUTATED")
            with self.assertRaises(ValueError):
                verify_private_stage124_archive(path, expected_size=size,
                                                expected_sha256=digest, checkpoints=2)

    def test_missing_frame_or_bad_png_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic.tar.gz"
            size, digest = archive_at(path, omit=("control", 120))
            with self.assertRaises(ValueError):
                verify_private_stage124_archive(path, expected_size=size,
                                                expected_sha256=digest, checkpoints=2)
            path.unlink()
            size, digest = archive_at(path, invalid_png=True)
            with self.assertRaisesRegex(ValueError, "invalid PNG"):
                verify_private_stage124_archive(path, expected_size=size,
                                                expected_sha256=digest, checkpoints=2)

    def test_missing_private_diagnostic_sidecar_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "missing-diagnostic.tar.gz"
            size, digest = archive_at(path, omit_sidecar=("enabled", "fad.vhcdlog"))
            with self.assertRaisesRegex(ValueError, "diagnostics missing"):
                verify_private_stage124_archive(path, expected_size=size,
                                                expected_sha256=digest, checkpoints=2)

    def test_symlinks_and_tar_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic.tar.gz"
            size, digest = archive_at(path, traversal=True)
            with self.assertRaisesRegex(ValueError, "unsafe archive path"):
                verify_private_stage124_archive(path, expected_size=size,
                                                expected_sha256=digest, checkpoints=2)
            path.unlink()
            size, digest = archive_at(path, symlink=True)
            with self.assertRaisesRegex(ValueError, "unsafe member type"):
                verify_private_stage124_archive(path, expected_size=size,
                                                expected_sha256=digest, checkpoints=2)
            alias = Path(folder) / "alias.tar.gz"
            alias.symlink_to(path)
            with self.assertRaisesRegex(ValueError, "absolute private archive"):
                verify_private_stage124_archive(alias, expected_size=size,
                                                expected_sha256=digest, checkpoints=2)

    def test_missing_archive_is_not_reported_as_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "missing.tar.gz"
            with self.assertRaises(ValueError):
                verify_private_stage124_archive(path, expected_size=1,
                                                expected_sha256="a" * 64, checkpoints=2)


if __name__ == "__main__":
    unittest.main()
