"""Subprocess-level tests for three independent NeXium trial workspaces."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "nexium_repeat_trials.sh"


def put(path, contents):
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o755)


class RepeatLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        (self.root / "nros").mkdir()
        (self.root / "bin").mkdir()
        (self.root / "runtime-evidence").mkdir()
        (self.root / "nros" / "vh_saturn_demo.nro").write_bytes(b"NRO0-SYNTHETIC")
        (self.root / "runtime-evidence" / "nexium-window.png").write_bytes(b"FRAME1")
        (self.root / "runtime-evidence" / "nexium.log").write_text("ALSA mock\n")
        put(self.root / "bin" / "xvfb-run",
            '#!/usr/bin/env bash\n'
            'while (( $# )); do\n'
            '  if [[ "$1" == "bash" ]]; then shift; exec bash "$@"; fi\n'
            '  shift\n'
            'done\nexit 8\n')
        put(self.root / "scripts" / "nexium_xvfb_session.sh",
            '#!/usr/bin/env bash\n'
            'set -e\n'
            'mkdir -p runtime-evidence\n'
            'printf "%s" "$PWD" > runtime-evidence/actual-workspace.txt\n'
            'printf synthetic > runtime-evidence/nexium-window.png\n'
            'echo "mock host log" > runtime-evidence/nexium.log\n'
            'if [[ "$PWD" == *trial-03* && "${MOCK_FAIL_THIRD:-0}" == 1 ]]; then exit 19; fi\n')
        self.env = dict(os.environ, PATH=f"{self.root / 'bin'}:{os.environ['PATH']}",
                        NEXIUM_BIN=str(self.root / "nros" / "vh_saturn_demo.nro"))

    def invoke(self):
        return subprocess.run(["bash", str(SCRIPT)], cwd=self.root, env=self.env,
                              capture_output=True, text=True, timeout=12)

    def test_syntax(self):
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True)

    def test_two_fresh_processes_in_isolated_dirs(self):
        run = self.invoke()
        self.assertEqual(run.returncode, 0, run.stderr)
        folder = self.root / "runtime-evidence" / "repeat-trials"
        self.assertEqual((folder / "trial-01" / "nexium-window.png").read_bytes(), b"FRAME1")
        for i in (2, 3):
            current = folder / f"trial-{i:02d}"
            self.assertEqual((current / "launcher-exit.txt").read_text().strip(), "0")
            self.assertIn(f"trial-{i:02d}/workspace",
                          (current / "actual-workspace.txt").read_text())
            self.assertFalse((current / "workspace").exists())

    def test_failed_third_trial_keeps_evidence_and_exit_code(self):
        self.env["MOCK_FAIL_THIRD"] = "1"
        run = self.invoke()
        self.assertEqual(run.returncode, 0, run.stderr)
        trial = self.root / "runtime-evidence" / "repeat-trials" / "trial-03"
        self.assertEqual((trial / "launcher-exit.txt").read_text().strip(), "19")
        self.assertTrue((trial / "nexium-window.png").is_file())
        # The separate strict audit must convert this failure into nonzero CI.
        self.assertNotIn("all_passed", run.stdout)

    def test_missing_initial_capture_fails_closed(self):
        (self.root / "runtime-evidence" / "nexium-window.png").unlink()
        run = self.invoke()
        self.assertNotEqual(run.returncode, 0)


if __name__ == "__main__":
    unittest.main()
