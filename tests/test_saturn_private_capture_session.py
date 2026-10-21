"""Stage86: fake-media-only offline tests of safe private Yabause capture."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from tools.saturn_private_capture_session import (
    GATE_FILE, LOG_FILE, RECEIPT_FILE, capture_private, inspect_log,
    inspect_sources, _private_empty_dir,
)

GOOD_TRACE = b"VHCD_FAD 150\nVHCD_FAD 151\n"
RUNNER = """import os
from pathlib import Path
Path(os.environ['VH_SATURN_FAD_LOG']).write_bytes(b'VHCD_FAD 150\\nVHCD_FAD 151\\n')
"""


class PrivateCaptureTests(unittest.TestCase):
    def setUp(self):
        self.root_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.root_tmp.cleanup)
        self.root = Path(self.root_tmp.name)
        self.source_dir = self.root / "private-source"
        self.source_dir.mkdir(mode=0o700)
        fake = {
            "track1": b"FAKE TRACK1 TEST ONLY 2352\n",
            "track2": b"FAKE TRACK2 TEST ONLY\n",
            "cue": b'FILE "NOT_REAL_TRACK1.BIN" BINARY\n',
        }
        self.pins = {}
        files = {}
        for role, blob in fake.items():
            path = self.source_dir / (role + ".txt")
            path.write_bytes(blob)
            self.pins[role] = (len(blob), hashlib.sha256(blob).hexdigest())
            files[role] = str(path)
        self.manifest = {
            "schema_version": 1, "product_code": "T-9526G",
            "release_kind": "translation_patched",
            "files": files,
        }
        self.workspace = self.root / "capture"
        self.workspace.mkdir(mode=0o700)
        os.chmod(self.workspace, 0o700)

    def run_capture(self, code=RUNNER):
        return capture_private(
            self.manifest, self.workspace, "menu_control",
            [sys.executable, "-c", code], seconds=10, pins=self.pins,
        )

    def test_real_process_synthetic_receipt_is_private_and_unverified(self):
        receipt = self.run_capture()
        self.assertEqual(receipt["numeric_fad_events"], 2)
        self.assertTrue(receipt["pinned_files_unchanged_after_run"])
        self.assertFalse(receipt["original_game_execution_verified"])
        self.assertFalse(receipt["scene_frame_synchronized_verified"])
        self.assertFalse(receipt["session_independence_verified"])
        self.assertEqual(set(x.name for x in self.workspace.iterdir()),
                         {LOG_FILE, RECEIPT_FILE})
        data = (self.workspace / RECEIPT_FILE).read_text()
        self.assertNotIn("FAKE TRACK", data)
        self.assertNotIn(str(self.source_dir), data)
        self.assertNotIn(self.pins["track1"][1], data)
        self.assertEqual((self.workspace / LOG_FILE).read_bytes(), GOOD_TRACE)

    def test_rejects_changed_source_and_never_claims_success(self):
        target = self.manifest["files"]["track1"]
        code = f"""from pathlib import Path
import os
p=Path({target!r})
p.write_bytes(b'changed')
Path(os.environ['VH_SATURN_FAD_LOG']).write_bytes(b'VHCD_FAD 150\\n')
"""
        with self.assertRaises(ValueError):
            self.run_capture(code)
        self.assertFalse((self.workspace / RECEIPT_FILE).exists())

    def test_source_pin_mismatch_rejected_before_launch(self):
        self.pins["track1"] = (1, "0" * 64)
        with self.assertRaises(ValueError):
            self.run_capture()
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_uncleared_gate_is_rejected(self):
        code = RUNNER + """
Path(os.environ['VH_SATURN_CAPTURE_GATE']).write_bytes(b'1\\n')
"""
        with self.assertRaises(ValueError):
            self.run_capture(code)
        self.assertFalse((self.workspace / RECEIPT_FILE).exists())

    def test_rejects_leaked_raw_sector_file(self):
        code = RUNNER + """
Path('sector.bin').write_bytes(b'FAKE GAME SECTOR')
"""
        with self.assertRaises(ValueError):
            self.run_capture(code)

    def test_rejects_extra_or_crlf_log(self):
        for raw in (b"VHCD_FAD 150\nSECRET\n", b"VHCD_FAD 150\r\n",
                    b"VHCD_FAD 150\nVHCD_FAD 001\n"):
            with self.subTest(raw=raw):
                (self.workspace / LOG_FILE).write_bytes(raw)
                with self.assertRaises(ValueError):
                    inspect_log(self.workspace / LOG_FILE)

    def test_rejects_symlink_source_even_if_hash_correct(self):
        origin = Path(self.manifest["files"]["cue"])
        alias = self.source_dir / "other-cue.txt"
        alias.symlink_to(origin)
        self.manifest["files"]["cue"] = str(alias)
        with self.assertRaises(ValueError):
            inspect_sources(self.manifest, pins=self.pins)

    def test_rejects_checkout_workspace(self):
        (self.root / ".git").mkdir()
        with self.assertRaises(ValueError):
            _private_empty_dir(self.workspace)

    def test_rejects_world_readable_workspace(self):
        os.chmod(self.workspace, 0o755)
        with self.assertRaises(ValueError):
            _private_empty_dir(self.workspace)

    def test_rejects_reused_workspace(self):
        (self.workspace / "existing").write_text("unrelated")
        with self.assertRaises(ValueError):
            self.run_capture()

    def test_rejects_wrong_phase_and_non_absolute_program(self):
        with self.assertRaises(ValueError):
            capture_private(self.manifest, self.workspace, "made_up_phase",
                            [sys.executable], pins=self.pins)
        with self.assertRaises(ValueError):
            capture_private(self.manifest, self.workspace, "menu_control",
                            ["python3", "-c", RUNNER], pins=self.pins)

    def test_rejects_nonzero_emulator_exit(self):
        with self.assertRaises(ValueError):
            self.run_capture("raise SystemExit(3)")
        self.assertFalse((self.workspace / RECEIPT_FILE).exists())


if __name__ == "__main__":
    unittest.main()
