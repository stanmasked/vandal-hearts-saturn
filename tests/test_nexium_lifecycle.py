"""Mock the real Bash launcher and check orderly X11 teardown and evidence."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'nexium_capture.sh'


def executable(path, data):
    path.write_text(data)
    path.chmod(0o755)


class LifecycleTests(unittest.TestCase):
    def launch(self, kind='graceful', before_panic=False):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'bin').mkdir()
            (root / 'nros').mkdir()
            (root / 'nros' / 'vh_saturn_demo.nro').write_bytes(b'FAKE')
            emu = root / 'bin' / 'nexium-mock'
            executable(emu, '#!/usr/bin/env bash\n'
                       'echo "$$" > emu.pid\n'
                       + ('echo "thread main panicked at BEFORE_CLOSE"\n' if before_panic else '')
                       + ('trap "exit 0" TERM\n' if kind != 'crash' else '')
                       + ('exit 7\n' if kind == 'crash' else 'while :; do sleep 0.1; done\n'))
             executable(root / 'bin' / 'xdotool',
                        '#!/usr/bin/env bash\n'
                        'if [[ "$1" == "search" ]]; then echo 456; exit 0; fi\n'
                        'if [[ "$1" == "getwindowgeometry" ]]; then printf "WINDOW=456\\nX=0\\nY=0\\nWIDTH=640\\nHEIGHT=480\\nSCREEN=0\\n"; exit 0; fi\n'
                        'if [[ "$1" == "windowclose" ]]; then\n'
                        + ('  exit 1\n' if kind == 'no_windowclose' else '  kill -TERM "$(cat emu.pid)"; exit 0\n')
                        + 'fi\n' + ('if [[ "$1" == "key" ]]; then sleep 30; fi\n' if kind == 'hung_key' else '') + 'exit 0\n')
            executable(root / 'bin' / 'xprop',
                       '#!/usr/bin/env bash\nprintf "WM_PROTOCOLS(ATOM): WM_DELETE_WINDOW\\n"\n')
            executable(root / 'bin' / 'wmctrl',
                       '#!/usr/bin/env bash\n' +
                       ('exit 1\n' if kind == 'no_windowclose' else
                        'kill -TERM "$(cat emu.pid)"; exit 0\n'))
             executable(root / 'bin' / 'ffmpeg',
                        '#!/usr/bin/env bash\n'
                        'out=""; for arg in "$@"; do out="$arg"; done; printf PNG_MOCK > "$out"\n')
            env = os.environ.copy()
            env.update(PATH=f'{root / "bin"}:{os.environ["PATH"]}',
                       NEXIUM_BIN=str(emu), NEXIUM_WINDOW_ATTEMPTS='2',
                       NEXIUM_POLL_DELAY_SECONDS='0', NEXIUM_SETTLE_DELAY_SECONDS='0',
                       NEXIUM_CLOSE_WAIT_SECONDS='1')
            p = subprocess.run(['bash', str(SCRIPT)], cwd=root, env=env, text=True,
                               capture_output=True, timeout=12)
            evidence = root / 'runtime-evidence'
            files = {}
            for name in ('lifecycle-status.txt', 'nexium-log-before-close.log',
                         'nexium.log', 'failure-reason.txt', 'capture-status.txt',
                         'input-probe-status.txt', 'nexium-window.png'):
                path = evidence / name
                files[name] = path.read_text() if path.exists() else None
            return p, files

    def test_shell_valid(self):
        subprocess.run(['bash', '-n', str(SCRIPT)], check=True)

    def test_graceful_close_succeeds(self):
        p, f = self.launch()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('windowclose_sent', f['lifecycle-status.txt'])
        self.assertIn('emulator_exit_code=0', f['lifecycle-status.txt'])
        self.assertNotIn('forced_sigterm', f['lifecycle-status.txt'])
        self.assertIsNone(f['failure-reason.txt'])
        self.assertEqual(f['nexium-window.png'], 'PNG_MOCK')
        self.assertIsNotNone(f['nexium-log-before-close.log'])

    def test_nonzero_early_exit_does_not_pass(self):
        p, f = self.launch(kind='crash')
        self.assertNotEqual(p.returncode, 0)
        self.assertIsNotNone(f['failure-reason.txt'])

    def test_unresponsive_window_triggers_forced_close(self):
        p, f = self.launch(kind='no_windowclose')
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(f['failure-reason.txt'], 'forced_termination_after_capture\n')
        self.assertIn('windowclose_unavailable', f['lifecycle-status.txt'])
        self.assertIn('forced_sigterm', f['lifecycle-status.txt'])

    def test_hung_input_probe_does_not_block_cleanup(self):
        p, f = self.launch(kind='hung_key')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(f['input-probe-status.txt'], 'input_attempted=Right dispatch=failed\n')
        self.assertIn('emulator_exit_code=0', f['lifecycle-status.txt'])
        self.assertIsNone(f['failure-reason.txt'])

    def test_before_close_panic_evidence_persists(self):
        p, f = self.launch(before_panic=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('panicked at BEFORE_CLOSE', f['nexium-log-before-close.log'])


if __name__ == '__main__':
    unittest.main()
