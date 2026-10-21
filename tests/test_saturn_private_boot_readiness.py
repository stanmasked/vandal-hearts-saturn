"""Stage93 synthetic-only end-to-end Track1+Track2+CUE+ISO9660 tests.

These tests invent an entire 22-sector Saturn-shaped image. They do NOT
contain, retrieve, unpack or publish actual Vandal Hearts game sectors.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import saturn_private_capture_session as private
from tools.saturn_private_boot_readiness import (
    _write_receipt, audit_boot_readiness,
)

RAW = 2352
EXPECTED = {
    "boot_product_code": "T-9526G",
    "volume_id": "VANDAL_HEARTS",
    "sectors": 22,
    "declared_iso_sectors": 22,
    "files": 1,
    "directories": 1,
    "extension_counts": {"BIN": 1},
}
RESOURCE_NAMES = frozenset({"MAP_1_1C.BIN"})


def both(value):
    return value.to_bytes(4, "little") + value.to_bytes(4, "big")


def record(name, extent, length, *, directory=False):
    name = name if isinstance(name, bytes) else name.encode("ascii")
    n = 33 + len(name) + (len(name) % 2 == 0)
    b = bytearray(n)
    b[0] = n
    b[2:10] = both(extent)
    b[10:18] = both(length)
    b[25] = 2 if directory else 0
    b[32] = len(name)
    b[33:33+len(name)] = name
    return b


def invented_iso(out, *, outside=False):
    sectors = [bytearray(2048) for _ in range(22)]
    sectors[0][:16] = b"SEGA SEGASATURN "
    sectors[0][40:47] = b"T-9526G"
    sectors[16][:7] = b"\x01CD001\x01"
    sectors[16][40:53] = b"VANDAL_HEARTS"
    sectors[16][80:88] = both(22)
    sectors[16][156:190] = record(b"\x00", 20, 2048, directory=True)
    entries = (record(b"\x00", 20, 2048, directory=True)
               + record(b"\x01", 20, 2048, directory=True)
               + record("MAP_1_1C.BIN;1", 200 if outside else 21, 100))
    sectors[20][:len(entries)] = entries
    with out.open("wb") as stream:
        for i, sector in enumerate(sectors):
            raw = (bytes.fromhex("00ffffffffffffffffffff00")
                   + bytes([0, 2, i % 60, 1]) + sector + bytes(288))
            assert len(raw) == RAW
            stream.write(raw)


class PrivateBootReadinessTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.root.chmod(0o700)
        self.track1 = self.root / "invented-track1.bin"
        self.track2 = self.root / "invented-track2.bin"
        self.cue = self.root / "invented.cue"
        invented_iso(self.track1)
        self.track2.write_bytes(bytes(RAW * 152))
        self.cue.write_bytes(
            b'CATALOG 0000000000000\n'
            b'FILE "invented-track1.bin" BINARY\n'
            b'  TRACK 01 MODE1/2352\n'
            b'    INDEX 01 00:00:00\n'
            b'FILE "invented-track2.bin" BINARY\n'
            b'  TRACK 02 AUDIO\n'
            b'    INDEX 00 00:00:00\n'
            b'    INDEX 01 00:02:00\n'
        )
        self.pin_ctx = patch.dict(private.PINNED, self._pins(), clear=True)
        self.pin_ctx.start()
        self.addCleanup(self.pin_ctx.stop)

    def _pins(self):
        return {role: (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
                for role, p in (("cue", self.cue), ("track1", self.track1),
                                ("track2", self.track2))}

    def audit(self, *, expected=None, resource_names=None):
        return audit_boot_readiness(
            self.cue, self.track1, self.track2,
            expected_iso=EXPECTED if expected is None else expected,
            expected_resources=RESOURCE_NAMES if resource_names is None else resource_names,
        )

    def test_complete_fake_synthetic_disc_passes_without_game_claim(self):
        receipt = self.audit()
        self.assertTrue(receipt["stage02_track1_sha256_verified_before_and_after"])
        self.assertTrue(receipt["iso9660_boot_header_and_product_code_verified"])
        self.assertTrue(receipt["source_snapshot_identity_stable"])
        self.assertEqual(receipt["logical_data_sector_count"], 22)
        self.assertEqual(receipt["iso_file_count"], 1)
        for name in ("original_game_boot_observed",
                     "real_first_battle_scene_observed",
                     "frame_synchronized_fad_read_verified",
                     "copyrighted_content_exported"):
            self.assertFalse(receipt[name])
        self.assertNotIn("invented-track1.bin", str(receipt))
        self.assertNotIn(str(self.root), str(receipt))
        self.assertNotIn(private.PINNED["track1"][1], str(receipt))

    def test_receipt_created_private_and_no_overwrite(self):
        receipt = self.audit()
        output = self.root / "receipt.json"
        _write_receipt(output, receipt)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(output.read_text()), receipt)
        with self.assertRaises(ValueError):
            _write_receipt(output, receipt)
        self.assertEqual(json.loads(output.read_text()), receipt)

    def test_wrong_full_track1_sha_rejected(self):
        self.track1.write_bytes(self.track1.read_bytes()[:-1] + b"Z")
        with self.assertRaises(ValueError):
            self.audit()

    def test_wrong_audio_hash_rejected(self):
        with self.track2.open("r+b") as f:
            f.seek(RAW * 151)
            f.write(b"X")
        with self.assertRaises(ValueError):
            self.audit()

    def test_missing_track1_rejected_not_metadata_substituted(self):
        self.track1.unlink()
        with self.assertRaises(OSError):
            self.audit()

    def test_unexpected_iso_inventory_rejected(self):
        expected = dict(EXPECTED)
        expected["files"] = 848
        with self.assertRaises(ValueError):
            self.audit(expected=expected)

    def test_absent_stage02_candidate_rejected(self):
        with self.assertRaises(ValueError):
            self.audit(resource_names=frozenset({"BATL1PRG.BIN"}))

    def test_corrupt_directory_extent_rejected_after_repin(self):
        invented_iso(self.track1, outside=True)
        with patch.dict(private.PINNED, self._pins(), clear=True):
            with self.assertRaises(ValueError):
                self.audit()

    def test_changed_media_during_iso_inspection_is_rejected(self):
        from tools import saturn_private_boot_readiness as tool
        original = tool.SaturnISO.inspect
        def mutate(instance, *, include_files=False):
            value = original(instance, include_files=include_files)
            with self.track1.open("r+b") as stream:
                stream.seek(RAW * 21 + 99)
                stream.write(b"!")  # mutate a sector byte AFTER the parsed inventory
            return value
        with patch.object(tool.SaturnISO, "inspect", mutate):
            with self.assertRaises(ValueError):
                self.audit()

    def test_cue_replaced_after_original_pin_rejected(self):
        self.cue.write_bytes(self.cue.read_bytes().replace(
            b"INDEX 01 00:02:00", b"INDEX 01 00:01:00",
        ))
        with self.assertRaises(ValueError):
            self.audit()

    def test_source_paths_inside_git_checkout_rejected(self):
        (self.root / ".git").mkdir()
        with self.assertRaises(ValueError):
            self.audit()

    def test_symlinked_track1_rejected(self):
        alias = self.root / "alias.bin"
        alias.symlink_to(self.track1)
        with self.assertRaises(ValueError):
            audit_boot_readiness(
                self.cue, alias, self.track2,
                expected_iso=EXPECTED, expected_resources=RESOURCE_NAMES,
            )

    def test_public_or_symlinked_receipt_destination_rejected(self):
        result = self.audit()
        self.root.chmod(0o755)
        with self.assertRaises(ValueError):
            _write_receipt(self.root / "receipt.json", result)
        self.root.chmod(0o700)
        target = self.root / "target"
        target.write_text("safe")
        dest = self.root / "receipt.json"
        dest.symlink_to(target)
        with self.assertRaises(ValueError):
            _write_receipt(dest, result)
        self.assertEqual(target.read_text(), "safe")


if __name__ == "__main__":
    unittest.main()
