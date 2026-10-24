"""Synthetic-only Stage145 runner input schedule tests; no original media or emulator."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.saturn_private_prologue_continue_twelfth_c import (
    CONFIRM10_PRESS, CONFIRM10_RELEASE, CONFIRM11_PRESS, CONFIRM11_RELEASE,
    CONFIRM12_PRESS, CONFIRM12_RELEASE, FRAME_COUNT, _run_one,
)


class _CompletedProcess:
    pid = 12345
    def wait(self, timeout=None):
        return 0


class TwelfthCRunnerScheduleTests(unittest.TestCase):
    def _run(self, twelfth):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td) / "cohort"
            directory.mkdir(mode=0o700)
            seen = {}
            def fake_popen(args, **kwargs):
                seen["args"] = args
                seen["env"] = kwargs["env"]
                seen["cwd"] = kwargs["cwd"]
                return _CompletedProcess()
            with patch("tools.saturn_private_prologue_continue_twelfth_c.subprocess.Popen", side_effect=fake_popen):
                _run_one(Path("/tmp/yabause-stage145"), Path("/tmp/original.cue"), directory,
                         twelfth=twelfth, seconds=10)
            return seen

    def test_runner_caps_at_144000_and_shares_tenth_and_eleventh_c(self):
        self.assertEqual(FRAME_COUNT, 144000)
        self.assertEqual((CONFIRM10_PRESS, CONFIRM10_RELEASE), (108000, 108006))
        self.assertEqual((CONFIRM11_PRESS, CONFIRM11_RELEASE), (120000, 120006))
        self.assertEqual((CONFIRM12_PRESS, CONFIRM12_RELEASE), (132000, 132006))
        control = self._run(False)
        env = control["env"]
        self.assertEqual(control["args"][-1], "144000")
        self.assertEqual(env["VH_SATURN_CONFIRM_AT_FRAME10"], "108000")
        self.assertEqual(env["VH_SATURN_CONFIRM10_ENABLED"], "1")
        self.assertEqual(env["VH_SATURN_CONFIRM_AT_FRAME11"], "120000")
        self.assertEqual(env["VH_SATURN_CONFIRM11_ENABLED"], "1")
        self.assertEqual(env["VH_SATURN_CONFIRM_AT_FRAME12"], "132000")
        self.assertEqual(env["VH_SATURN_CONFIRM12_ENABLED"], "0")

    def test_only_intervention_enables_twelfth_c(self):
        control = self._run(False)["env"]
        intervention = self._run(True)["env"]
        self.assertEqual(control["VH_SATURN_CONFIRM12_ENABLED"], "0")
        self.assertEqual(intervention["VH_SATURN_CONFIRM12_ENABLED"], "1")
        for key in ("VH_SATURN_CONFIRM_AT_FRAME10", "VH_SATURN_CONFIRM10_ENABLED",
                    "VH_SATURN_CONFIRM_AT_FRAME11", "VH_SATURN_CONFIRM11_ENABLED",
                    "VH_SATURN_CONFIRM_AT_FRAME12"):
            self.assertEqual(control[key], intervention[key])


if __name__ == "__main__":
    unittest.main()
