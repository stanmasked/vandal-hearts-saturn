"""Stage87: synthetic launcher and source-path binding, no game files."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from tools.saturn_private_capture_session import (
    LOG_FILE, RECEIPT_FILE, capture_private,
)

SCRIPT = '''#!/usr/bin/env python3
import os
from pathlib import Path
Path(os.environ["VH_SATURN_FAD_LOG"]).write_bytes(b"VHCD_FAD 150\\n")
'''


class RunnerBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = self.root / "source"
        source.mkdir(mode=0o700)
        fake = {
            "track1": b"INVENTED_TRACK1",
            "track2": b"INVENTED_TRACK2",
            "cue": b"INVENTED_CUE",
        }
        self.pins = {}
        paths = {}
        for name, content in fake.items():
            file = source / (name + ".fake")
            file.write_bytes(content)
            paths[name] = str(file)
            self.pins[name] = (len(content), hashlib.sha256(content).hexdigest())
        self.manifest = {
            "schema_version": 1,
            "product_code": "T-9526G",
            "release_kind": "translation_patched",
            "files": paths,
        }
        self.runner = self.root / "public-emulator-test-only"
        self.runner.write_text(SCRIPT, encoding="utf-8")
        self.runner.chmod(0o700)
        self.expected = hashlib.sha256(self.runner.read_bytes()).hexdigest()
        self.workspace = self.root / "private-session"
        self.workspace.mkdir(mode=0o700)
        self.workspace.chmod(0o700)

    def command(self):
        return [str(self.runner), self.manifest["files"]["cue"]]

    def capture(self, command=None, pin=None):
        return capture_private(
            self.manifest, self.workspace, "menu_control",
            command if command is not None else self.command(), seconds=10,
            pins=self.pins,
            expected_executable_sha256=self.expected if pin is None else pin,
        )

    def test_pinned_runner_and_exact_cue_token_pass_but_no_game_claim(self):
        result = self.capture()
        self.assertTrue(result["runner_matches_separately_supplied_sha256"])
        self.assertTrue(result["cue_path_exactly_present_in_command"])
        self.assertFalse(result["emulator_binary_origin_independently_verified"])
        self.assertFalse(result["game_disc_actually_opened_verified"])
        self.assertFalse(result["original_game_execution_verified"])
        self.assertEqual(result["numeric_fad_events"], 1)
        receipt = (self.workspace / RECEIPT_FILE).read_text()
        self.assertNotIn(self.expected, receipt)
        self.assertNotIn(str(self.runner), receipt)
        self.assertNotIn(self.manifest["files"]["cue"], receipt)
        self.assertEqual((self.workspace / LOG_FILE).read_bytes(),
                         b"VHCD_FAD 150\n")

    def test_wrong_runner_digest_blocks_before_process(self):
        with self.assertRaises(ValueError):
            self.capture(pin="0" * 64)
        self.assertFalse(any(self.workspace.iterdir()))

    def test_bad_digest_format_blocks(self):
        with self.assertRaises(ValueError):
            self.capture(pin="F" * 64)
        with self.assertRaises(ValueError):
            self.capture(pin="not-a-sha")
        self.assertFalse(any(self.workspace.iterdir()))

    def test_omitted_cue_argument_blocks(self):
        with self.assertRaises(ValueError):
            self.capture(command=[str(self.runner)])
        self.assertFalse(any(self.workspace.iterdir()))

    def test_similar_but_not_exact_cue_path_blocks(self):
        with self.assertRaises(ValueError):
            self.capture(command=[str(self.runner),
                                  self.manifest["files"]["cue"] + ".other"])
        self.assertFalse(any(self.workspace.iterdir()))

    def test_symlinked_executable_rejected(self):
        alias = self.root / "alias-runner"
        alias.symlink_to(self.runner)
        with self.assertRaises(ValueError):
            self.capture(command=[str(alias), self.manifest["files"]["cue"]])

    def test_hardlinked_executable_rejected(self):
        alias = self.root / "hardlink-runner"
        os.link(self.runner, alias)
        with self.assertRaises(ValueError):
            self.capture()

    def test_changed_executable_before_start_rejected(self):
        self.runner.write_text(SCRIPT + "\n# changed", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.capture()
        self.assertFalse((self.workspace / RECEIPT_FILE).exists())

    def test_changed_executable_during_run_rejected(self):
        self.runner.write_text(SCRIPT + '''
with open(__file__, "ab") as f:
    f.write(b"\\n# changed at runtime")
''', encoding="utf-8")
        new_pin = hashlib.sha256(self.runner.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            self.capture(pin=new_pin)
        self.assertFalse((self.workspace / RECEIPT_FILE).exists())

    def test_runner_missing_or_nonabsolute_blocks(self):
        with self.assertRaises(ValueError):
            self.capture(command=["relative-runner", self.manifest["files"]["cue"]])
        self.assertFalse(any(self.workspace.iterdir()))

    def test_runner_source_change_still_fails(self):
        changer = SCRIPT + '''
from pathlib import Path
Path(__file__).with_name("source").joinpath("track1.fake").write_bytes(b"modified")
'''
        self.runner.write_text(changer, encoding="utf-8")
        pin = hashlib.sha256(self.runner.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            self.capture(pin=pin)
        self.assertFalse((self.workspace / RECEIPT_FILE).exists())


if __name__ == "__main__":
    unittest.main()
