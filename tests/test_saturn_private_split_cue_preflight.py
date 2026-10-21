"""Stage90 invented-input CUE structure and private completeness safeguards."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.saturn_private_split_cue_preflight import (
    inspect_cue, audit_private_cue,
)
from tools import saturn_private_split_cue_preflight as preflight

FAKE_CUE = (
    b"CATALOG 0000000000000\n"
    b'FILE "invented-data.bin" BINARY\n'
    b"  TRACK 01 MODE1/2352\n"
    b"    INDEX 01 00:00:00\n"
    b'FILE "invented-audio.bin" BINARY\n'
    b"  TRACK 02 AUDIO\n"
    b"    INDEX 00 00:00:00\n"
    b"    INDEX 01 00:02:00\n"
)


def check(raw=FAKE_CUE, n1=2 * 2352, n2=152 * 2352):
    return inspect_cue(raw, track1_bytes=n1, track2_bytes=n2)


class SaturnSplitCueTests(unittest.TestCase):
    def test_expected_fad_math_for_two_file_fixture(self):
        data = check()
        self.assertEqual(data["data_sector_count"], 2)
        self.assertEqual(data["data_fad_start"], 150)
        self.assertEqual(data["data_fad_end"], 151)
        self.assertEqual(data["audio_index01_fad"], 302)
        self.assertEqual(data["audio_fad_end"], 303)
        self.assertEqual(data["leadout_fad"], 304)

    def test_stage02_declared_sizes_give_expected_numeric_ranges(self):
        data = check(n1=621755904, n2=2102688)
        self.assertEqual(data["data_sector_count"], 264352)
        self.assertEqual(data["data_fad_end"], 264501)
        self.assertEqual(data["audio_file_sector_count"], 894)
        self.assertEqual(data["audio_pregap_sectors"], 150)
        self.assertEqual(data["active_audio_sector_count"], 744)
        self.assertEqual(data["audio_index01_fad"], 264652)
        self.assertEqual(data["audio_fad_end"], 265395)

    def test_malformed_or_extra_cue_commands_fail_closed(self):
        variants = (
            FAKE_CUE + b"REM unexpected\n",
            FAKE_CUE.replace(b"TRACK 02 AUDIO", b"TRACK 03 AUDIO"),
            FAKE_CUE.replace(b"TRACK 01 MODE1/2352", b"TRACK 01 MODE2/2352"),
            FAKE_CUE.replace(b"INDEX 01 00:02:00", b"INDEX 01 00:01:00"),
            FAKE_CUE.replace(b"INDEX 00 00:00:00", b"INDEX 00 00:00:01"),
            FAKE_CUE.replace(b"CATALOG 0000000000000", b"CATALOG BAD"),
            FAKE_CUE.replace(b"FILE \"invented-audio.bin\"", b'FILE "../escape.bin"'),
            FAKE_CUE.replace(b"FILE \"invented-audio.bin\"", b'FILE "invented-data.bin"'),
        )
        for raw in variants:
            with self.subTest(raw=raw[:45]), self.assertRaises(ValueError):
                check(raw)

    def test_invalid_track_lengths_rejected(self):
        for n1, n2 in ((0, 152*2352), (2353, 152*2352),
                       (2*2352, 150*2352), (2*2352, 150*2352+2),
                       (True, 152*2352)):
            with self.subTest(n1=n1, n2=n2), self.assertRaises(ValueError):
                check(n1=n1, n2=n2)

    def test_nonascii_and_oversized_cue_rejected(self):
        for raw in (b"", b"\xff" + FAKE_CUE, FAKE_CUE + b" " * 9000):
            with self.subTest(n=len(raw)), self.assertRaises(ValueError):
                check(raw)

    def test_private_partial_vs_full_source_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw1, raw2 = bytes(2*2352), bytes(152*2352)
            files = {
                "cue": root/"test.cue",
                "track1": root/"invented-data.bin",
                "track2": root/"invented-audio.bin",
            }
            files["cue"].write_bytes(FAKE_CUE)
            files["track1"].write_bytes(raw1)
            files["track2"].write_bytes(raw2)
            fakepins = {
                name: (len(file.read_bytes()), hashlib.sha256(file.read_bytes()).hexdigest())
                for name,file in files.items()
            }
            with patch.dict(preflight.PINNED, fakepins, clear=True):
                partial = audit_private_cue(
                    files["cue"], files["track2"],
                    track1_metadata_name="invented-data.bin",
                    track1_metadata_size=2*2352,
                )
                self.assertFalse(partial["local_media_ready_for_capture"])
                self.assertFalse(partial["data_track_stage02_sha256_verified"])
                self.assertEqual(partial["blockers"], ["TRACK1_CONTENT_NOT_LOCALLY_HASH_VERIFIED"])
                full = audit_private_cue(
                    files["cue"], files["track2"], track1=files["track1"],
                )
                self.assertTrue(full["local_media_ready_for_capture"])
                self.assertTrue(full["data_track_stage02_sha256_verified"])
                self.assertEqual(full["blockers"], [])
                self.assertFalse(full["original_game_boot_verified"])
                self.assertFalse(full["resource_loader_verified"])
                self.assertNotIn(str(root), str(full))
                self.assertNotIn("invented-data.bin", str(full))

    def test_actual_audio_content_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            cue, audio=root/"test.cue",root/"invented-audio.bin"
            cue.write_bytes(FAKE_CUE)
            audio.write_bytes(bytes(152*2352))
            pins = {
                "track1": (2*2352, "0"*64),
                "cue": (len(FAKE_CUE), hashlib.sha256(FAKE_CUE).hexdigest()),
                "track2": (audio.stat().st_size, hashlib.sha256(audio.read_bytes()).hexdigest()),
            }
            audio.write_bytes(b"!" + audio.read_bytes()[1:])
            with patch.dict(preflight.PINNED, pins, clear=True):
                with self.assertRaises(ValueError):
                    audit_private_cue(
                        cue,audio,track1_metadata_name="invented-data.bin",
                        track1_metadata_size=2*2352,
                    )


if __name__ == "__main__":
    unittest.main()
