"""Actual Bash subprocess tests of Stage46 bounded visual X11 Right input.

The stub controls image output only; script runs its real Pillow motion
decoder. A dispatched xdotool key never proves a visible cursor move.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw
from tools.nexium_guest_evidence import EXPECTED_INPUT_RECEIPT

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "nexium_right_probe.sh"


def scene(path: Path, x: int):
    im = Image.new("RGB", (1280, 720), (15, 19, 32))
    ImageDraw.Draw(im).rectangle((x, 270, x + 55, 302), fill=(230, 178, 62))
    im.save(path)


def executable(path: Path, contents: str):
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o755)


class RightProbeTests(unittest.TestCase):
    def scenario(self, shifts, *, attempts=None):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "runtime-evidence").mkdir()
            (root / "bin").mkdir()
            scene(root / "runtime-evidence/nexium-window.png", 400)
            for index, delta in enumerate(shifts, start=1):
                scene(root / f"frame-{index}.png", 400 + delta)
            executable(root / "bin/xdotool",
                       "#!/usr/bin/env bash\n"
                       "if [[ \"$1\" == \"key\" ]]; then echo key >> key-count.txt; fi\n"
                       "if [[ \"$1\" == \"windowfocus\" ]]; then echo focused >> focus.txt; fi\n"
                       "exit 0\n")
            executable(root / "bin/import",
                       "#!/usr/bin/env bash\n"
                       "out=\"${@: -1}\"\n"
                       "idx=\"${out##*-}\"\n"
                       "idx=\"${idx%.png}\"\n"
                       "cp \"frame-$idx.png\" \"$out\"\n")
            env = dict(os.environ,
                       PATH=f"{root / 'bin'}:{os.environ['PATH']}",
                       PYTHONPATH=str(ROOT),
                       NEXIUM_PROBE_PYTHON=sys.executable,
                       NEXIUM_PROBE_MAX_ATTEMPTS=str(
                           len(shifts) if attempts is None else attempts))
            result = subprocess.run(["bash", str(SCRIPT), "123456"],
                                    cwd=root, env=env, capture_output=True,
                                    text=True, timeout=25)
            base = root / "runtime-evidence"
            receipt_path = base / "input-probe-attempts.txt"
            status_path = base / "input-probe-status.txt"
            selected = base / "nexium-after-right.png"
            keys = root / "key-count.txt"
            focus = root / "focus.txt"
            return (result, receipt_path.read_text(),
                    status_path.read_text(),
                    len(keys.read_text().splitlines()) if keys.exists() else 0,
                    len(focus.read_text().splitlines()) if focus.exists() else 0,
                    selected.read_bytes() if selected.exists() else None,
                    sorted(p.name for p in base.glob("nexium-after-right-attempt-*.png")))

    def test_shell_syntax(self):
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True)

    def test_first_frame_moves_no_retry(self):
        p, receipt, status, keys, focused, selected, images = self.scenario([35])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("probe=bounded_right_v2", receipt)
        self.assertIn("selected_attempt=1", receipt)
        self.assertIn("attempt1=visible_movement", receipt)
        self.assertEqual(keys, 1)
        self.assertEqual(focused, 0)
        self.assertEqual(status.strip(), EXPECTED_INPUT_RECEIPT)
        self.assertIsNotNone(selected)
        self.assertEqual(len(images), 1)

    def test_static_first_frame_retry_moves_and_is_selected(self):
        p, receipt, status, keys, focused, selected, images = self.scenario([0, 35])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("attempt1=no_verified_movement", receipt)
        self.assertIn("attempt2=visible_movement", receipt)
        self.assertIn("selected_attempt=2", receipt)
        self.assertEqual(keys, 2)
        self.assertEqual(focused, 1)
        self.assertEqual(status.strip(), EXPECTED_INPUT_RECEIPT)
        self.assertEqual(len(images), 2)
        with tempfile.TemporaryDirectory() as temp:
            filepath = Path(temp) / "selected.png"
            filepath.write_bytes(selected)
            with Image.open(filepath) as im:
                self.assertEqual(im.getpixel((435, 270)), (230, 178, 62))

    def test_sixth_pulse_moves_and_first_five_are_preserved(self):
        p, receipt, status, keys, focused, selected, images = self.scenario(
            [0, 0, 0, 0, 0, 35])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(keys, 6)
        self.assertEqual(focused, 5)
        self.assertIn("selected_attempt=6", receipt)
        self.assertIn("attempt6=visible_movement", receipt)
        self.assertEqual(status.strip(), EXPECTED_INPUT_RECEIPT)
        self.assertIsNotNone(selected)
        self.assertEqual(len(images), 6)

    def test_three_static_frames_remain_unverified(self):
        p, receipt, status, keys, focused, selected, images = self.scenario(
            [0, 0, 0])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("attempt3=no_verified_movement", receipt)
        self.assertIn("selected_attempt=none", receipt)
        self.assertEqual(keys, 3)
        self.assertEqual(focused, 2)
        self.assertIn("motion=unverified", status)
        self.assertIsNone(selected)
        self.assertEqual(len(images), 3)

    def test_hung_xdotool_aborts_after_one_timeout(self):
        # The four-second dispatch timeout must not multiply eightfold.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "bin").mkdir()
            (root / "runtime-evidence").mkdir()
            scene(root / "runtime-evidence/nexium-window.png", 400)
            executable(root / "bin/xdotool",
                       "#!/usr/bin/env bash\n"
                       'if [[ "$1" == "key" ]]; then sleep 30; fi\n'
                       "exit 0\n")
            env = dict(os.environ,
                       PATH=f"{root / 'bin'}:{os.environ['PATH']}",
                       NEXIUM_PROBE_MAX_ATTEMPTS="8")
            p = subprocess.run(["bash", str(SCRIPT), "123456"],
                               cwd=root, env=env,
                               capture_output=True, text=True, timeout=9)
            self.assertEqual(p.returncode, 0, p.stderr)
            status = (root / "runtime-evidence/input-probe-status.txt").read_text()
            receipt = (root / "runtime-evidence/input-probe-attempts.txt").read_text()
            self.assertEqual(status, "input_attempted=Right dispatch=failed\n")
            self.assertIn("attempt1=dispatch_failed", receipt)
            self.assertIn("selected_attempt=none", receipt)
            self.assertNotIn("attempt2=", receipt)
            self.assertFalse((root / "runtime-evidence/nexium-after-right.png").exists())

    def test_bad_id_rejected_without_command(self):
        p = subprocess.run(["bash", str(SCRIPT), "123;echo BAD"],
                           capture_output=True, text=True, timeout=3)
        self.assertEqual(p.returncode, 4)

    def test_attempts_above_eight_rejected(self):
        p = subprocess.run(
            ["bash", str(SCRIPT), "123456"],
            env=dict(os.environ, NEXIUM_PROBE_MAX_ATTEMPTS="9"),
            capture_output=True, text=True, timeout=3)
        self.assertEqual(p.returncode, 4)


if __name__ == "__main__":
    unittest.main()
