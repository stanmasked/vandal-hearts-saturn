"""Run NeXium capture orchestration against mock executables, no game assets."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / 'scripts' / 'nexium_capture.sh'


def executable(folder: Path, name: str, contents: str) -> Path:
    path = folder / name
    path.write_text(contents, encoding='utf8')
    path.chmod(0o755)
    return path


class LauncherIntegrationTests(unittest.TestCase):
    def launch(self, *, window=True, crash=False, capture_ok=True, attempts=2,
               settle=0, bogus_time=None):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            bin_dir = root / 'bin'
            bin_dir.mkdir()
            nro = root / 'nros'
            nro.mkdir()
            (nro / 'vh_saturn_demo.nro').write_bytes(b'ROM-FREE-MOCK')
            emu = executable(bin_dir, 'mock-emu',
                             '#!/usr/bin/env bash\n' +
                             ('echo MOCK_FAIL; exit 9\n' if crash else
                              'echo MOCK_START; while :; do [[ -f wm-close-requested ]] && exit 0; sleep 0.1; done\n'))
            executable(bin_dir, 'xdotool', '#!/usr/bin/env bash\n' +
                       ('echo 123456\n' if window else 'exit 1\n'))
            executable(bin_dir, 'xprop', '#!/usr/bin/env bash\nprintf "WM_PROTOCOLS(ATOM): WM_DELETE_WINDOW\\n"\n')
            executable(bin_dir, 'wmctrl', '#!/usr/bin/env bash\ntouch wm-close-requested; exit 0\n')
            executable(bin_dir, 'import', '#!/usr/bin/env bash\n' +
                       ('printf PNG_MOCK > "$3"\n' if capture_ok else 'exit 42\n'))
            env = dict(os.environ, PATH=f'{bin_dir}:{os.environ["PATH"]}',
                       NEXIUM_BIN=str(emu), NEXIUM_WINDOW_ATTEMPTS=str(attempts),
                       NEXIUM_POLL_DELAY_SECONDS='0', NEXIUM_SETTLE_DELAY_SECONDS=str(settle),
                       NEXIUM_CLOSE_WAIT_SECONDS='2',
                       # This launcher test uses literal PNG_MOCK, not a cursor
                       # image. Right-key recovery is tested separately with
                       # real synthetic PNG pixels in test_nexium_right_probe.
                       NEXIUM_PROBE_MAX_ATTEMPTS='1')
            if bogus_time is not None:
                env['NEXIUM_WINDOW_ATTEMPTS'] = bogus_time
            result = subprocess.run(['bash', str(CAPTURE)], cwd=root, env=env,
                                    text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=10)
            evidence = root / 'runtime-evidence'
            return result, {
                file: (evidence / file).read_text() if (evidence / file).exists() else None
                for file in ('failure-reason.txt', 'capture-status.txt', 'x11-close-status.txt', 'nexium.log',
                             'nexium-window.png')
            }

    def test_script_parses(self):
        subprocess.run(['bash', '-n', str(CAPTURE)], check=True)

    def test_happy_path_captures_nonempty_image_and_receipt(self):
        result, files = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('captured_window_id=123456', files['capture-status.txt'])
        self.assertIn('wmctrl_close_request_sent', files['x11-close-status.txt'])
        self.assertEqual(files['nexium-window.png'], 'PNG_MOCK')
        self.assertIsNone(files['failure-reason.txt'])
        self.assertIn('MOCK_START', files['nexium.log'])

    def test_emulator_early_crash(self):
        result, files = self.launch(window=False, crash=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(files['failure-reason.txt'], 'emulator_terminated_before_window\n')
        self.assertIn('MOCK_FAIL', files['nexium.log'])

    def test_emulator_stays_up_but_no_window(self):
        result, files = self.launch(window=False, attempts=2)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(files['failure-reason.txt'], 'window_not_found\n')

    def test_window_capture_failure_is_recorded(self):
        result, files = self.launch(capture_ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(files['failure-reason.txt'], 'window_capture_command_failed\n')

    def test_reject_bad_runtime_parameter(self):
        result, files = self.launch(bogus_time='2; rm -rf /')
        self.assertEqual(result.returncode, 4)
        self.assertIsNone(files['nexium.log'])


if __name__ == '__main__':
    unittest.main()
