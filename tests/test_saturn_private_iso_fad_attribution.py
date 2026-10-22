"""Stage100 fabricated-only FAD-to-ISO9660 extent tests, no copyrighted media."""
from pathlib import Path
import hashlib
import tempfile
import unittest
from unittest.mock import patch

from tools import saturn_private_capture_session as private
from tools.saturn_private_iso_fad_attribution import (
    parse_numeric_gated_fad_log, attribute_fad_events,
    audit_private_original_fad_files, write_private_attribution_report,
)
from test_saturn_private_boot_readiness import (
    invented_iso, RAW, EXPECTED, RESOURCE_NAMES,
)


class PrivateIsoReadAttributionTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.root.chmod(0o700)
        self.track1 = self.root / "invented-data.bin"
        self.track2 = self.root / "invented-audio.bin"
        self.cue = self.root / "invented-disc.cue"
        invented_iso(self.track1)
        self.track2.write_bytes(bytes(RAW*152))
        self.cue.write_bytes(
            b"CATALOG 0000000000000\n"
            b'FILE "invented-data.bin" BINARY\n'
            b"  TRACK 01 MODE1/2352\n"
            b"    INDEX 01 00:00:00\n"
            b'FILE "invented-audio.bin" BINARY\n'
            b"  TRACK 02 AUDIO\n"
            b"    INDEX 00 00:00:00\n"
            b"    INDEX 01 00:02:00\n"
        )
        self.capture = self.root / "capture"
        self.capture.mkdir(mode=0o700)
        self.log = self.capture / "fad.vhcdlog"
        self.log.write_bytes(
            b"VHCD_FAD 150\nVHCD_FAD 171\nVHCD_FAD 171\nVHCD_FAD 322\n"
        )
        self.log.chmod(0o600)
        pins = {
            name: (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
            for name,p in {
                "cue": self.cue, "track1": self.track1, "track2": self.track2
            }.items()
        }
        ctx=patch.dict(private.PINNED, pins, clear=True)
        ctx.start()
        self.addCleanup(ctx.stop)

    def audit(self):
        return audit_private_original_fad_files(
            self.cue, self.track1, self.track2, self.log,
            expected_iso=EXPECTED, expected_resources=RESOURCE_NAMES,
        )

    def test_original_cd_addresses_are_only_interval_intersections(self):
        result=self.audit()
        summary=result["summary"]
        self.assertEqual(summary["numeric_callback_fad_events"], 4)
        self.assertEqual(summary["unique_physical_fads"], 3)
        self.assertEqual(summary["events_in_named_file_extents"], 2)
        self.assertEqual(summary["events_outside_named_file_extents"], 1)
        self.assertEqual(summary["events_in_cd_audio"], 1)
        self.assertEqual(summary["distinct_named_files_touched"], 1)
        self.assertEqual(result["private_file_details"][0]["name"], "MAP_1_1C.BIN")
        self.assertEqual(result["private_file_details"][0]["event_count"], 2)
        self.assertEqual(summary["candidate_battle_resource_hits"]["MAP_1_1C.BIN"], 2)
        self.assertEqual(summary["candidate_battle_resource_hits"]["BATL1PRG.BIN"], 0)
        self.assertFalse(summary["actual_game_loader_causality_verified"])
        self.assertFalse(summary["original_game_scene_or_first_battle_verified"])
        self.assertNotIn(str(self.root), str(summary))

    def test_private_0600_nonoverwriting_report(self):
        out=self.root/"reports"
        out.mkdir(mode=0o700)
        target=write_private_attribution_report(out,self.audit())
        self.assertEqual(target.stat().st_mode & 0o777,0o600)
        with self.assertRaises(ValueError):
            write_private_attribution_report(out,self.audit())

    def test_corrupt_source_hash_refused(self):
        with self.track1.open("r+b") as stream:
            stream.seek(2352*21+32)
            stream.write(b"!")
        with self.assertRaises(ValueError):
            self.audit()

    def test_corrupt_cue_hash_refused(self):
        self.cue.write_bytes(self.cue.read_bytes()+b"?")
        with self.assertRaises(ValueError):
            self.audit()

    def test_noncanonical_fad_strings_rejected(self):
        for raw in (
            b"", b"VHCD_FAD 00171\n", b"VHCD_FAD -1\n",
            b"VHCD_FAD 171", b"VHCD_FAD 171\r\n",
            b"VHCD_FAD 171\nsecret\n", b"VHCD_FAD 4294967296\n",
        ):
            with self.subTest(data=raw):
                self.log.write_bytes(raw)
                with self.assertRaises(ValueError):
                    parse_numeric_gated_fad_log(self.log)

    def test_world_readable_capture_logs_refused(self):
        self.log.chmod(0o644)
        with self.assertRaises(ValueError):
            self.audit()

    def test_iso_extent_overlap_never_invents_unique_owner(self):
        info = [
            {"name":"invented-a.bin","lba":21,"bytes":12},
            {"name":"invented-b.bin","lba":21,"bytes":2048}
        ]
        report=attribute_fad_events(
            [171,171],info,data_sector_count=22,
            audio_index01_fad=322,leadout_fad=324,
        )["summary"]
        self.assertEqual(report["events_in_named_file_extents"],2)
        self.assertEqual(report["events_with_multiple_possible_file_owners"],2)
        self.assertFalse(report["actual_game_loader_causality_verified"])

    def test_fad_outside_disc_rejected(self):
        info=[{"name":"fake.bin","lba":21,"bytes":4}]
        for fad in (149,324, 2**32, True):
            with self.subTest(fad=fad),self.assertRaises(ValueError):
                attribute_fad_events(
                    [fad],info,data_sector_count=22,
                    audio_index01_fad=322,leadout_fad=324,
                )

    def test_invalid_iso_extent_refused(self):
        with self.assertRaises(ValueError):
            attribute_fad_events(
                [171],[{"name":"fake.bin","lba":21,"bytes":4096}],
                data_sector_count=22,audio_index01_fad=322,leadout_fad=324
            )

    def test_fad_log_symlink_and_unexpected_output_blocked(self):
        alias=self.root/"alias"
        self.log.rename(alias)
        self.log.symlink_to(alias)
        with self.assertRaises((ValueError,OSError)):
            self.audit()


if __name__ == "__main__":
    unittest.main()
