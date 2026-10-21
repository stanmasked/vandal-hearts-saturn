"""Synthetic process-level integration tests for the Xvfb/Openbox wrapper."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/nexium_xvfb_session.sh'


def put(path: Path, source: str):
    path.write_text(source, encoding='utf8')
    path.chmod(0o755)


class WindowManagerSessionTests(unittest.TestCase):
    def run_session(self, *, ready=True, wm_crashes=False, guest_result=0,
                    bad_setting=None, wm_ignores_term=False, wm_dies_after_ready=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binpath = root / 'bin'
            binpath.mkdir()
            (root / 'scripts').mkdir()
            put(binpath / 'openbox', '#!/usr/bin/env bash\n' +
                ('echo CRASH; exit 4\n' if wm_crashes else
                 ('echo MOCK_OPENBOX; sleep 0.2; exit 0\n' if wm_dies_after_ready else
                  ('trap \'\' TERM; echo MOCK_OPENBOX; while :; do sleep 0.1; done\n' if wm_ignores_term else
                   'echo MOCK_OPENBOX; sleep 10\n'))))
            put(binpath / 'wmctrl', '#!/usr/bin/env bash\n' +
                ('echo "Name: Openbox"\n' if ready else 'exit 1\n'))
            put(root / 'scripts/nexium_capture.sh',
                '#!/usr/bin/env bash\necho mock_guest_executed > guest-receipt.txt\n' +
                ('sleep 0.5\n' if wm_dies_after_ready else '') + f'exit {guest_result}\n')
            env = os.environ.copy()
            env.update(DISPLAY=':99', PATH=f'{binpath}:{env["PATH"]}',
                       NEXIUM_WM_WAIT_ATTEMPTS='2', NEXIUM_WM_POLL_SECONDS='0')
            if bad_setting is not None:
                env['NEXIUM_WM_WAIT_ATTEMPTS'] = bad_setting
            result = subprocess.run(['bash', str(SCRIPT)], cwd=root, env=env,
                                    capture_output=True, text=True, timeout=8)
            def contents(path):
                p = root / path
                return p.read_text() if p.exists() else None
            return result, {
                'status': contents('runtime-evidence/window-manager-status.txt'),
                'error': contents('runtime-evidence/window-manager-failure.txt'),
                'guest': contents('guest-receipt.txt'),
                'shutdown': contents('runtime-evidence/window-manager-shutdown.txt'),
            }

    def test_valid_bash_syntax(self):
        subprocess.run(['bash', '-n', str(SCRIPT)], check=True)

    def test_ready_window_manager_proceeds_to_guest(self):
        proc, files = self.run_session()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('window_manager=Openbox', files['status'])
        self.assertIn('mock_guest_executed', files['guest'])
        self.assertIsNone(files['error'])
        self.assertEqual(files['shutdown'], 'window_manager_reaped\n')

    def test_guest_failure_propagates_nonzero(self):
        proc, files = self.run_session(guest_result=19)
        self.assertEqual(proc.returncode, 19, proc.stderr)
        self.assertIsNotNone(files['status'])

    def test_window_manager_unavailable_fails_before_guest(self):
        proc, files = self.run_session(ready=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(files['error'], 'window_manager_not_ready\n')
        self.assertIsNone(files['guest'])

    def test_dead_window_manager_cannot_pass(self):
        proc, files = self.run_session(ready=False, wm_crashes=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(files['error'], 'window_manager_terminated\n')
        self.assertIsNone(files['guest'])

    def test_stubborn_window_manager_fails_instead_of_hanging(self):
        proc, files = self.run_session(wm_ignores_term=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(files['shutdown'], 'window_manager_forced_sigkill\n')
        self.assertIsNotNone(files['guest'])

    def test_window_manager_dies_during_guest_capture(self):
        proc, files = self.run_session(wm_dies_after_ready=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(files['error'], 'window_manager_died_during_capture\n')

    def test_malformed_attempt_limit_rejected(self):
        proc, files = self.run_session(bad_setting='2; true')
        self.assertEqual(proc.returncode, 4)
        self.assertIsNone(files['guest'])


if __name__ == '__main__':
    unittest.main()
