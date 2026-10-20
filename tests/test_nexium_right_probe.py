"""Real Bash subprocess checks of bounded screenshot-confirmed Right retry."""
from __future__ import annotations
import os
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
# Test in the local stage directory; CI uses equivalent repository placement.
SCRIPT = ROOT / 'scripts' / 'nexium_right_probe.sh'


def scene(path: Path, x: int):
    im = Image.new('RGB', (1280, 720), (15, 19, 32))
    ImageDraw.Draw(im).rectangle((x, 270, x + 55, 302), fill=(230, 178, 62))
    im.save(path)


def executable(path: Path, contents: str):
    path.write_text(contents)
    path.chmod(0o755)


class RightProbeTests(unittest.TestCase):
    def scenario(self, first_shift: int, second_shift: int):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'runtime-evidence').mkdir()
            (root / 'bin').mkdir()
            scene(root / 'runtime-evidence/nexium-window.png', 400)
            scene(root / 'first.png', 400 + first_shift)
            scene(root / 'second.png', 400 + second_shift)
            executable(root / 'bin/xdotool', '#!/usr/bin/env bash\n'
                       'if [[ "$1" == "key" ]]; then echo key >> key-count.txt; fi\n'
                       'if [[ "$1" == "windowfocus" ]]; then echo focused > focus.txt; fi\n'
                       'exit 0\n')
            executable(root / 'bin/import', '#!/usr/bin/env bash\n'
                       'if [[ "$3" == *retry.png ]]; then cp second.png "$3"; else cp first.png "$3"; fi\n')
            env = dict(os.environ, PATH=f'{root / "bin"}:{os.environ["PATH"]}',
                       PYTHONPATH=str(ROOT), NEXIUM_PROBE_PYTHON=sys.executable)
            result = subprocess.run(['bash', str(SCRIPT), '123456'], cwd=root, env=env,
                                    capture_output=True, text=True, timeout=14)
            base = root / 'runtime-evidence'
            return (result,
                    (base / 'input-probe-attempts.txt').read_text(),
                    (base / 'input-probe-status.txt').read_text(),
                    len((root / 'key-count.txt').read_text().splitlines()),
                    (root / 'focus.txt').exists(),
                    (base / 'nexium-after-right.png').read_bytes())

    def test_shell_syntax(self):
        subprocess.run(['bash', '-n', str(SCRIPT)], check=True)

    def test_first_frame_moves_no_retry(self):
        p, receipt, status, attempts, focused, _ = self.scenario(35, 0)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('selected_attempt=1', receipt)
        self.assertIn('attempt1=visible_movement', receipt)
        self.assertEqual(attempts, 1)
        self.assertFalse(focused)
        self.assertIn('screenshot=ready', status)

    def test_static_first_frame_retry_moves_and_is_selected(self):
        p, receipt, status, attempts, focused, selected = self.scenario(0, 35)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('attempt1=no_verified_movement', receipt)
        self.assertIn('attempt2=visible_movement', receipt)
        self.assertIn('selected_attempt=2', receipt)
        self.assertEqual(attempts, 2)
        self.assertTrue(focused)
        with tempfile.TemporaryDirectory() as temp:
            selected_path = Path(temp) / 'selected.png'
            selected_path.write_bytes(selected)
            with Image.open(selected_path) as im:
                self.assertEqual(im.getpixel((435, 270)), (230, 178, 62))

    def test_both_static_remain_unverified(self):
        p, receipt, _, attempts, focused, _ = self.scenario(0, 0)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('attempt2=no_verified_movement', receipt)
        self.assertNotIn('attempt2=visible_movement', receipt)
        self.assertEqual(attempts, 2)
        self.assertTrue(focused)

    def test_bad_id_rejected_without_command(self):
        p = subprocess.run(['bash', str(SCRIPT), '123;echo BAD'],
                           capture_output=True, text=True, timeout=3)
        self.assertEqual(p.returncode, 4)


if __name__ == '__main__':
    unittest.main()
