"""Stage94: only invented Saturn data and a synthetic executable are used."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import saturn_private_capture_session as private
from tools import saturn_private_boot_handoff as handoff
from tools.saturn_private_boot_handoff import (
    HANDOFF_RECEIPT, run_private_handoff,
)
from test_saturn_private_boot_readiness import (
    invented_iso, RAW, EXPECTED, RESOURCE_NAMES,
)

FAKE_RUNNER = '''#!/usr/bin/env python3
import os
from pathlib import Path
Path(os.environ["VH_SATURN_FAD_LOG"]).write_bytes(b"VHCD_FAD 150\\n")
'''


class Stage94HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        self.track1 = self.root / "fake-data.bin"
        self.track2 = self.root / "fake-audio.bin"
        self.cue = self.root / "fake-saturn.CUE"
        invented_iso(self.track1)
        self.track2.write_bytes(bytes(RAW * 152))
        self.cue.write_bytes(
            b"CATALOG 0000000000000\n"
            b'FILE "fake-data.bin" BINARY\n'
            b"  TRACK 01 MODE1/2352\n"
            b"    INDEX 01 00:00:00\n"
            b'FILE "fake-audio.bin" BINARY\n'
            b"  TRACK 02 AUDIO\n"
            b"    INDEX 00 00:00:00\n"
            b"    INDEX 01 00:02:00\n"
        )
        self.exe = self.root / "synthetic-runner"
        self.exe.write_text(FAKE_RUNNER)
        self.exe.chmod(0o700)
        self.pin = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        self.workspace = self.root / "capture"
        self.workspace.mkdir(mode=0o700)
        self.workspace.chmod(0o700)
        self.ctx = patch.dict(private.PINNED, self._pins(), clear=True)
        self.ctx.start()
        self.addCleanup(self.ctx.stop)

    def _pins(self):
        return {
            key: (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
            for key, p in {
                "cue": self.cue, "track1": self.track1, "track2": self.track2
            }.items()
        }

    def call(self, *, runner=None, command=None, pin=None, phase="menu_control"):
        return run_private_handoff(
            self.cue, self.track1, self.track2, self.workspace, phase,
            [str(self.exe), str(self.cue)] if command is None else command,
            self.pin if pin is None else pin,
            seconds=10, expected_iso=EXPECTED,
            expected_resources=RESOURCE_NAMES,
            pins=private.PINNED,
        )

    def test_three_layer_handoff_receipt_is_explicitly_unverified_gameplay(self):
        out = self.call()
        self.assertEqual(out["numeric_only_fad_event_count"], 1)
        self.assertTrue(out["full_stage02_disc_preflight_before_and_after"])
        self.assertTrue(out["declared_executable_sha256_matched_before_and_after"])
        self.assertFalse(out["original_saturn_game_boot_verified"])
        self.assertFalse(out["game_disc_actually_opened_independently_verified"])
        self.assertFalse(out["original_first_battle_screen_verified"])
        self.assertEqual(
            {p.name for p in self.workspace.iterdir()},
            {HANDOFF_RECEIPT, private.LOG_FILE, private.RECEIPT_FILE},
        )
        report = (self.workspace / HANDOFF_RECEIPT).read_text()
        self.assertNotIn(str(self.root), report)
        self.assertNotIn(self.pin, report)
        self.assertNotIn(private.PINNED["track1"][1], report)
        self.assertEqual(
            (self.workspace / HANDOFF_RECEIPT).stat().st_mode & 0o777, 0o600
        )

    def test_invalid_runner_pin_rejected_before_process(self):
        with self.assertRaises(ValueError):
            self.call(pin="f" * 64)
        self.assertFalse(list(self.workspace.iterdir()))

    def test_wrong_command_cue_refused(self):
        with self.assertRaises(ValueError):
            self.call(command=[str(self.exe), str(self.cue) + ".other"])
        self.assertFalse(list(self.workspace.iterdir()))

    def test_missing_track1_fails_before_launch(self):
        self.track1.unlink()
        with self.assertRaises(OSError):
            self.call()
        self.assertFalse(list(self.workspace.iterdir()))

    def test_false_stage02_inventory_refuses_boot_readiness(self):
        with patch.object(handoff, "audit_boot_readiness", side_effect=ValueError("wrong-ISO")):
            with self.assertRaises(ValueError):
                self.call()
        self.assertFalse(list(self.workspace.iterdir()))

    def test_corrupt_audio_byte_is_rejected(self):
        with self.track2.open("r+b") as stream:
            stream.seek(RAW * 150)
            stream.write(b"!")
        with self.assertRaises(ValueError):
            self.call()
        self.assertFalse(list(self.workspace.iterdir()))

    def test_mutation_during_run_never_emits_handoff_receipt(self):
        self.exe.write_text(FAKE_RUNNER + f'''
with open({str(self.track1)!r}, "r+b") as f:
    f.seek(2352 * 21 + 70)
    f.write(b"changed")
''')
        self.pin = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            self.call()
        self.assertFalse((self.workspace / HANDOFF_RECEIPT).exists())
        self.assertFalse((self.workspace / private.RECEIPT_FILE).exists())

    def test_revalidation_failure_revokes_lower_assurance_receipt(self):
        real = handoff.audit_boot_readiness
        counter = [0]
        def return_then_refuse(*args, **kwargs):
            counter[0] += 1
            if counter[0] == 2:
                raise ValueError("source changed after capture")
            return real(*args, **kwargs)
        with patch.object(handoff, "audit_boot_readiness", return_then_refuse):
            with self.assertRaises(ValueError):
                self.call()
        self.assertFalse((self.workspace / private.RECEIPT_FILE).exists())
        self.assertFalse((self.workspace / HANDOFF_RECEIPT).exists())
        self.assertEqual(counter[0], 2)

    def test_gate_left_open_blocks_handoff(self):
        self.exe.write_text(FAKE_RUNNER + '''
Path(os.environ["VH_SATURN_CAPTURE_GATE"]).write_bytes(b"1\\n")
''')
        self.pin = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            self.call()
        self.assertFalse((self.workspace / HANDOFF_RECEIPT).exists())

    def test_unexpected_output_blocks_handoff(self):
        self.exe.write_text(FAKE_RUNNER + '''
Path("unapproved.dat").write_bytes(b"fabricated")
''')
        self.pin = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            self.call()
        self.assertFalse((self.workspace / HANDOFF_RECEIPT).exists())

    def test_dirty_workspace_and_in_checkout_are_rejected(self):
        (self.workspace / "old").write_text("old")
        with self.assertRaises(ValueError):
            self.call()
        (self.workspace / "old").unlink()
        (self.root / ".git").mkdir()
        with self.assertRaises(ValueError):
            self.call()

    def test_runner_modified_at_runtime_is_rejected(self):
        self.exe.write_text(FAKE_RUNNER + '''
with open(__file__, "ab") as f:
    f.write(b"\\n# changed")
''')
        self.pin = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            self.call()
        self.assertFalse((self.workspace / HANDOFF_RECEIPT).exists())

    def test_wrong_phase_not_authenticity_proof(self):
        with self.assertRaises(ValueError):
            self.call(phase="invented_phase")
        self.assertFalse((self.workspace / HANDOFF_RECEIPT).exists())


if __name__ == "__main__":
    unittest.main()
