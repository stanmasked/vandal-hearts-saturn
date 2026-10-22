"""Stage96 invented PNG files bound to genuine fake-process Stage94 receipts."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from tools import saturn_private_capture_session as private
from tools.saturn_private_boot_handoff import run_private_handoff
from tools.saturn_private_frame_witness import (
    WITNESS_NAME, audit_frame_witnesses, validate_png_file,
)
from test_saturn_private_boot_readiness import (
    invented_iso, RAW, EXPECTED, RESOURCE_NAMES,
)

FAKE_RUNNER = '''#!/usr/bin/env python3
import os
from pathlib import Path
import sys
mode=sys.argv[1]
Path(os.environ["VH_SATURN_FAD_LOG"]).write_bytes(
    b"VHCD_FAD 150\\n" if mode=="menu" else b"VHCD_FAD 151\\n")
'''


def chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))


def png(r, g, b):
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(bytes([0, r, g, b]))) +
            chunk(b"IEND", b""))


def png_gray_1bit(sample=0):
    scanline = bytes([0, (sample & 1) << 7])
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 1, 0, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(scanline)) +
            chunk(b"IEND", b""))


def png_truecolor_1bit():
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 1, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(bytes([0, 0, 0, 0]))) +
            chunk(b"IEND", b""))


def png_indexed_8bit(include_palette=True):
    palette = chunk(b"PLTE", bytes([0, 0, 0, 255, 255, 255])) if include_palette else b""
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 3, 0, 0, 0)) +
            palette +
            chunk(b"IDAT", zlib.compress(bytes([0, 0])) +
            chunk(b"IEND", b""))


class FrameWitnessIntegrityTests(unittest.TestCase):
    def test_valid_low_bit_depth_grayscale_png_is_accepted(self):
        self.assertEqual(validate_png_file(png_gray_1bit()), (1, 1))
        self.assertEqual(validate_png_file(png_gray_1bit(1)), (1, 1))

    def test_low_bit_depth_truecolor_png_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported PNG frame shape"):
            validate_png_file(png_truecolor_1bit())

    def test_valid_indexed_png_is_accepted(self):
        self.assertEqual(validate_png_file(png_indexed_8bit()), (1, 1))

    def test_indexed_png_without_palette_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing palette"):
            validate_png_file(png_indexed_8bit(include_palette=False))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.track1 = self.root / "invented-track1.bin"
        self.track2 = self.root / "invented-track2.bin"
        self.cue = self.root / "invented-disc.CUE"
        invented_iso(self.track1)
        self.track2.write_bytes(bytes(RAW * 152))
        self.cue.write_bytes(
            b"CATALOG 0000000000000\n"
            b'FILE "invented-track1.bin" BINARY\n'
            b"  TRACK 01 MODE1/2352\n"
            b"    INDEX 01 00:00:00\n"
            b'FILE "invented-track2.bin" BINARY\n'
            b"  TRACK 02 AUDIO\n"
            b"    INDEX 00 00:00:00\n"
            b"    INDEX 01 00:02:00\n"
        )
        self.exe = self.root / "invented-runner"
        self.exe.write_text(FAKE_RUNNER)
        self.exe.chmod(0o700)
        runner_sha = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        pins = {
            role: (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
            for role, p in {
                "track1": self.track1, "track2": self.track2,
                "cue": self.cue,
            }.items()
        }
        ctx = patch.dict(private.PINNED, pins, clear=True)
        ctx.start()
        self.addCleanup(ctx.stop)
        self.sessions = []
        for i, (phase, mode) in enumerate((
            ("menu_control", "menu"), ("menu_control", "menu"),
            ("first_battle_entry", "battle"),
            ("first_battle_entry", "battle"),
        )):
            folder = self.root / f"capture-{i}"
            folder.mkdir(mode=0o700)
            run_private_handoff(
                self.cue, self.track1, self.track2, folder, phase,
                [str(self.exe), mode, str(self.cue)], runner_sha,
                seconds=10, expected_iso=EXPECTED,
                expected_resources=RESOURCE_NAMES, pins=private.PINNED,
            )
            witness = self.root / f"witness-{i}"
            witness.mkdir(mode=0o700)
            capture_receipt = json.loads(
                (folder / private.RECEIPT_FILE).read_text()
            )
            log_bytes = (folder / private.LOG_FILE).read_bytes()
            manifest = {
                "schema_version": 1,
                "session_id": capture_receipt["session_id"],
                "phase": phase,
                "numeric_fad_sha256": hashlib.sha256(log_bytes).hexdigest(),
                "frames": [],
            }
            for k, name in enumerate(("before.png", "after.png")):
                data = png(2 + i, 3 + k, 4)
                file = witness / name
                file.write_bytes(data)
                file.chmod(0o600)
                manifest["frames"].append({
                    "when": "before_gate" if k == 0 else "after_gate",
                    "file": name,
                    "declared_frame_counter": 10 if k == 0 else 20,
                    "sha256": hashlib.sha256(data).hexdigest(),
                })
            sidecar = witness / WITNESS_NAME
            sidecar.write_text(json.dumps(manifest))
            sidecar.chmod(0o600)
            self.sessions.append((phase, folder, witness))

    def audit(self, sessions=None):
        return audit_frame_witnesses(
            self.sessions if sessions is None else sessions,
            track1_sectors=22,
        )

    def modify(self, index, callback):
        file = self.sessions[index][2] / WITNESS_NAME
        record = json.loads(file.read_text())
        callback(record)
        file.write_text(json.dumps(record))
        file.chmod(0o600)

    def test_four_cohort_png_pairs_and_numeric_receipt_binding(self):
        out = self.audit()
        self.assertEqual(out["locally_present_frame_files_verified"], 8)
        self.assertTrue(out["all_fad_logs_bound_by_sha256_to_frame_sidecars"])
        self.assertTrue(out["stage95_cohort_sources_and_fad_verified"])
        self.assertFalse(out["frame_capture_synchronized_to_fad_gate_verified"])
        self.assertFalse(out["original_first_battle_scene_identified"])
        self.assertNotIn(str(self.root), str(out))
        self.assertNotIn(hashlib.sha256(png(1, 2, 3)).hexdigest(), str(out))

    def test_changed_frame_bytes_refused(self):
        file = self.sessions[0][2] / "before.png"
        data = bytearray(file.read_bytes())
        data[-6] ^= 1
        file.write_bytes(data)
        file.chmod(0o600)
        with self.assertRaises(ValueError):
            self.audit()

    def test_invalid_png_chunk_crc_refused_even_with_updated_digest(self):
        file = self.sessions[0][2] / "before.png"
        data = bytearray(file.read_bytes())
        data[20] ^= 1
        file.write_bytes(data)
        file.chmod(0o600)
        self.modify(0, lambda d: d["frames"][0].update({
            "sha256": hashlib.sha256(data).hexdigest()
        }))
        with self.assertRaises(ValueError):
            self.audit()

    def test_reused_witness_folder_refused(self):
        altered = self.sessions[:3] + [(
            self.sessions[3][0], self.sessions[3][1], self.sessions[0][2]
        )]
        with self.assertRaises(ValueError):
            self.audit(altered)

    def test_mismatched_session_identifier_refused(self):
        self.modify(0, lambda d: d.update({
            "session_id": self.sessions[1][2].name
        }))
        with self.assertRaises(ValueError):
            self.audit()

    def test_wrong_phase_refused(self):
        self.modify(2, lambda d: d.update({"phase": "menu_control"}))
        with self.assertRaises(ValueError):
            self.audit()

    def test_changed_numeric_fad_hash_refused(self):
        self.modify(0, lambda d: d.update({"numeric_fad_sha256": "0" * 64}))
        with self.assertRaises(ValueError):
            self.audit()

    def test_nonmonotone_self_declared_counters_refused(self):
        self.modify(0, lambda d: d["frames"][1].update({
            "declared_frame_counter": 10
        }))
        with self.assertRaises(ValueError):
            self.audit()

    def test_bool_counter_refused(self):
        self.modify(0, lambda d: d["frames"][1].update({
            "declared_frame_counter": True
        }))
        with self.assertRaises(ValueError):
            self.audit()

    def test_frame_symlink_rejected(self):
        original = self.sessions[0][2] / "before.png"
        alias = self.root / "shared.png"
        alias.write_bytes(original.read_bytes())
        original.unlink()
        original.symlink_to(alias)
        with self.assertRaises(ValueError):
            self.audit()

    def test_unexpected_file_and_world_readable_rejected(self):
        folder = self.sessions[0][2]
        (folder / "leaked-content.bin").write_bytes(b"synthetic")
        with self.assertRaises(ValueError):
            self.audit()
        (folder / "leaked-content.bin").unlink()
        (folder / "before.png").chmod(0o644)
        with self.assertRaises(ValueError):
            self.audit()

    def test_same_png_before_and_after_is_legal_not_scene_proof(self):
        folder = self.sessions[0][2]
        original = (folder / "before.png").read_bytes()
        (folder / "after.png").write_bytes(original)
        (folder / "after.png").chmod(0o600)
        self.modify(0, lambda d: d["frames"][1].update({
            "sha256": hashlib.sha256(original).hexdigest()
        }))
        out = self.audit()
        self.assertEqual(out["unchanged_png_pairs"], 1)
        self.assertFalse(out["original_first_battle_scene_identified"])

    def test_malformed_or_incomplete_png_rejected(self):
        original = png(1, 2, 3)
        for changed in (original[:-1], original + b"extra",
                        b"not-png", original[:28] + b"?" + original[29:]):
            with self.subTest(length=len(changed)), self.assertRaises(ValueError):
                validate_png_file(changed)


if __name__ == "__main__":
    unittest.main()
