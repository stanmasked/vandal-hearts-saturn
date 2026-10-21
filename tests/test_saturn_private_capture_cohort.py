"""Stage95 end-to-end four invented Stage94 handoffs and cohort audit."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import saturn_private_capture_session as private
from tools.saturn_private_boot_handoff import (
    HANDOFF_RECEIPT, run_private_handoff,
)
from tools.saturn_private_capture_cohort import (
    audit_four_capture_cohort, _write_private_json,
)
from tools.saturn_read_crosswalk import ADDRESSING
from test_saturn_private_boot_readiness import (
    invented_iso, RAW, EXPECTED, RESOURCE_NAMES,
)

FAKE = '''#!/usr/bin/env python3
import os
from pathlib import Path
import sys
# Four actual separate fake Python subprocesses, not original Yabause.
mode=sys.argv[1]
payload=(b"VHCD_FAD 150\\nVHCD_FAD 151\\n" if mode=="menu"
         else b"VHCD_FAD 151\\nVHCD_FAD 152\\n")
Path(os.environ["VH_SATURN_FAD_LOG"]).write_bytes(payload)
'''


class FourCaptureCohortTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.root.chmod(0o700)
        self.track1 = self.root / "fake-track1.bin"
        self.track2 = self.root / "fake-track2.bin"
        self.cue = self.root / "fake-disc.CUE"
        invented_iso(self.track1)
        self.track2.write_bytes(bytes(152 * RAW))
        self.cue.write_bytes(
            b"CATALOG 0000000000000\n"
            b'FILE "fake-track1.bin" BINARY\n'
            b"  TRACK 01 MODE1/2352\n"
            b"    INDEX 01 00:00:00\n"
            b'FILE "fake-track2.bin" BINARY\n'
            b"  TRACK 02 AUDIO\n"
            b"    INDEX 00 00:00:00\n"
            b"    INDEX 01 00:02:00\n"
        )
        self.exe = self.root / "invented-runner"
        self.exe.write_text(FAKE)
        self.exe.chmod(0o700)
        self.exe_sha = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        self.pins = {
            role: (path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest())
            for role, path in {
                "track1": self.track1,
                "track2": self.track2,
                "cue": self.cue,
            }.items()
        }
        pins = patch.dict(private.PINNED, self.pins, clear=True)
        pins.start()
        self.addCleanup(pins.stop)
        self.sessions = []
        for phase, mode in (
            ("menu_control", "menu"),
            ("menu_control", "menu"),
            ("first_battle_entry", "battle"),
            ("first_battle_entry", "battle"),
        ):
            directory = self.root / ("run-" + str(len(self.sessions)))
            directory.mkdir(mode=0o700)
            directory.chmod(0o700)
            run_private_handoff(
                self.cue, self.track1, self.track2, directory, phase,
                [str(self.exe), mode, str(self.cue)], self.exe_sha,
                seconds=10, expected_iso=EXPECTED,
                expected_resources=RESOURCE_NAMES,
                pins=private.PINNED,
            )
            self.sessions.append((phase, directory))

    def audit(self, sessions=None):
        return audit_four_capture_cohort(
            self.sessions if sessions is None else sessions,
            track1_sectors=22,
        )

    def edit_json(self, index, name, change):
        file = self.sessions[index][1] / name
        obj = json.loads(file.read_text())
        change(obj)
        file.write_text(json.dumps(obj))
        file.chmod(0o600)

    def test_four_real_fake_processes_have_distinct_private_sessions(self):
        report, trace = self.audit()
        self.assertEqual(report["validated_stage94_capture_workspaces"], 4)
        self.assertEqual(report["distinct_self_reported_session_ids"], 4)
        self.assertEqual(report["declared_menu_sessions"], 2)
        self.assertEqual(report["declared_battle_entry_sessions"], 2)
        self.assertEqual(trace["addressing"], ADDRESSING)
        self.assertEqual(len(trace["runs"]), 4)
        self.assertEqual(trace["runs"][0]["reads"][0]["lba"], 0)
        self.assertEqual(trace["runs"][2]["reads"][0]["lba"], 1)
        self.assertEqual(report["identical_numeric_trace_pairs_by_phase"],
                         {"menu_control": 1, "first_battle_entry": 1})
        self.assertFalse(report["actual_independent_emulator_processes_verified"])
        self.assertFalse(report["original_first_battle_screen_observed"])
        self.assertNotIn(str(self.root), str(report))
        self.assertNotIn(self.exe_sha, str(report))
        self.assertEqual(
            (self.sessions[0][1] / private.LOG_FILE).stat().st_mode & 0o777,
            0o600,
        )

    def test_missing_session_fails(self):
        with self.assertRaises(ValueError):
            self.audit(self.sessions[:3])

    def test_reused_folder_or_symlink_fails(self):
        with self.assertRaises(ValueError):
            self.audit(self.sessions[:3] + [self.sessions[0]])
        alias = self.root / "alias-run"
        alias.symlink_to(self.sessions[0][1], target_is_directory=True)
        with self.assertRaises(ValueError):
            self.audit([(self.sessions[0][0], alias)] + self.sessions[1:])

    def test_swapped_or_missing_phase_rejected(self):
        changed = list(self.sessions)
        changed[0] = ("first_battle_entry", changed[0][1])
        with self.assertRaises(ValueError):
            self.audit(changed)

    def test_duplicate_self_reported_session_id_refused(self):
        receipt = self.sessions[0][1] / private.RECEIPT_FILE
        existing = json.loads(receipt.read_text())["session_id"]
        self.edit_json(2, private.RECEIPT_FILE,
                       lambda d: d.update({"session_id": existing}))
        with self.assertRaises(ValueError):
            self.audit()

    def test_fad_count_disagrees_with_either_receipt(self):
        self.edit_json(0, HANDOFF_RECEIPT,
                       lambda d: d.update({"numeric_only_fad_event_count": 900}))
        with self.assertRaises(ValueError):
            self.audit()

    def test_corrupt_or_audio_fad_rejected(self):
        file = self.sessions[2][1] / private.LOG_FILE
        file.write_bytes(b"VHCD_FAD 264652\n")
        file.chmod(0o600)
        self.edit_json(2, HANDOFF_RECEIPT,
                       lambda d: d.update({"numeric_only_fad_event_count": 1}))
        self.edit_json(2, private.RECEIPT_FILE,
                       lambda d: d.update({"numeric_fad_events": 1}))
        with self.assertRaises(ValueError):
            self.audit()

    def test_private_log_rejects_world_readable_permissions(self):
        (self.sessions[0][1] / private.LOG_FILE).chmod(0o644)
        with self.assertRaises(ValueError):
            self.audit()

    def test_log_symlink_or_hardlink_refused(self):
        original = self.sessions[0][1] / private.LOG_FILE
        alias = self.root / "other"
        alias.write_bytes(original.read_bytes())
        original.unlink()
        original.symlink_to(alias)
        with self.assertRaises(ValueError):
            self.audit()

    def test_extra_files_are_refused(self):
        (self.sessions[0][1] / "unapproved-sector.bin").write_bytes(b"fake")
        with self.assertRaises(ValueError):
            self.audit()

    def test_corrupted_lower_receipt_is_rejected(self):
        self.edit_json(1, private.RECEIPT_FILE,
                       lambda d: d.update({"pinned_files_unchanged_after_run": False}))
        with self.assertRaises(ValueError):
            self.audit()

    def test_gameplay_truth_cannot_be_claimed_from_numeric_log(self):
        self.edit_json(0, HANDOFF_RECEIPT,
                       lambda d: d.update({"original_first_battle_screen_verified": True}))
        with self.assertRaises(ValueError):
            self.audit()

    def test_private_summary_and_trace_are_separate_0600_outputs(self):
        summary, trace = self.audit()
        out = self.root / "normalized"
        out.mkdir(mode=0o700)
        _write_private_json(out / "cohort.json", summary)
        _write_private_json(out / "trace.json", trace)
        self.assertEqual(json.loads((out / "cohort.json").read_text()), summary)
        self.assertEqual((out / "trace.json").stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError):
            _write_private_json(out / "trace.json", trace)

    def test_modified_log_line_endings_are_rejected(self):
        file = self.sessions[0][1] / private.LOG_FILE
        file.write_bytes(b"VHCD_FAD 150\r\nVHCD_FAD 151\n")
        file.chmod(0o600)
        with self.assertRaises(ValueError):
            self.audit()


if __name__ == "__main__":
    unittest.main()
