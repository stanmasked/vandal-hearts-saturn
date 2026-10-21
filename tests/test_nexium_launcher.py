"""Stage 22: ROM-free validation of NeXium launch shell syntax."""
from pathlib import Path
import subprocess
import unittest


class NexiumLaunchTests(unittest.TestCase):
    def test_shell_script_parses(self):
        root = Path(__file__).resolve().parents[1]
        script = root / "scripts" / "nexium_capture.sh"
        self.assertTrue(script.is_file())
        subprocess.run(["bash", "-n", str(script)], check=True, capture_output=True)

    def test_no_nested_bash_string(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "scripts" / "nexium_capture.sh").read_text(encoding="utf-8")
        self.assertNotIn("bash -c", source)
        self.assertIn("nexium-window.png", source)
        self.assertIn("nexium.log", source)


if __name__ == "__main__":
    unittest.main()
