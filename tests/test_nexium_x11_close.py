"""Real shell subprocess tests with fake X11 tools; no actual NeXium boot."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'nexium_x11_close.sh'


def put(path: Path, source: str) -> None:
    path.write_text(source, encoding='utf-8')
    path.chmod(0o755)


class X11CloseTests(unittest.TestCase):
    def probe(self, scenario='okay', window='4194306', timeout=1):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bins = root / 'bin'
            bins.mkdir()
            protocols = ('WM_PROTOCOLS(ATOM): protocols WM_DELETE_WINDOW, _NET_WM_PING\n'
                         if scenario != 'no_protocol' else
                         'WM_PROTOCOLS(ATOM): protocols _NET_WM_PING\n')
            put(bins / 'xprop', '#!/usr/bin/env bash\n' +
                ('exit 8\n' if scenario == 'query_failure' else
                 f'printf "%s" {protocols!r}\n'))
            put(bins / 'wmctrl', '#!/usr/bin/env bash\n' +
                ('sleep 20\n' if scenario == 'hung_close' else
                 'exit 3\n' if scenario == 'close_failure' else
                 'printf "CLOSE %s %s\\n" "$1" "$2" > wm-request.txt\n'))
            env = os.environ.copy()
            env['PATH'] = f'{bins}:{env["PATH"]}'
            env['NEXIUM_X11_CLOSE_TIMEOUT_SECONDS'] = str(timeout)
            p = subprocess.run(['bash', str(SCRIPT), window], cwd=root, env=env,
                               text=True, capture_output=True, timeout=7)
            file = root / 'runtime-evidence' / 'x11-close-status.txt'
            return p, file.read_text() if file.exists() else '', (root / 'wm-request.txt').exists()

    def test_valid_shell_syntax(self):
        subprocess.run(['bash', '-n', str(SCRIPT)], check=True)

    def test_supported_protocol_routes_through_wm(self):
        p, receipt, called = self.probe()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(called)
        self.assertIn('wm_delete_protocol_present', receipt)
        self.assertIn('wmctrl_close_request_sent', receipt)

    def test_missing_protocol_never_closes(self):
        p, receipt, called = self.probe('no_protocol')
        self.assertEqual(p.returncode, 2)
        self.assertFalse(called)
        self.assertIn('wm_delete_protocol_missing', receipt)

    def test_xprop_error_fails_closed(self):
        p, receipt, called = self.probe('query_failure')
        self.assertEqual(p.returncode, 2)
        self.assertFalse(called)
        self.assertIn('wm_protocol_query_failed', receipt)

    def test_window_manager_error_recorded(self):
        p, receipt, called = self.probe('close_failure')
        self.assertEqual(p.returncode, 3)
        self.assertFalse(called)
        self.assertIn('wmctrl_close_request_failed', receipt)

    def test_hung_window_manager_request_is_bounded(self):
        p, receipt, called = self.probe('hung_close')
        self.assertEqual(p.returncode, 3, p.stderr)
        self.assertFalse(called)
        self.assertIn('wmctrl_close_request_failed', receipt)

    def test_malformed_window_id_is_rejected(self):
        p, receipt, called = self.probe(window='4194306;rm')
        self.assertEqual(p.returncode, 4)
        self.assertFalse(called)

    def test_bad_timeout_is_rejected(self):
        p, receipt, called = self.probe(timeout='1;false')
        self.assertEqual(p.returncode, 4)
        self.assertFalse(called)


if __name__ == '__main__':
    unittest.main()
