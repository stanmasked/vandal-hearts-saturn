"""Stage77: synthetic capture gate verification, no original Saturn media."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.saturn_capture_gate import MARKER, set_capture_gate
from tools.saturn_yabause_gated_hook import patch_gated_cdbase
from test_saturn_yabause_capture import SOURCE


class ManualWindowTests(unittest.TestCase):
    def test_gate_marker_atomic_open_and_close(self):
        with tempfile.TemporaryDirectory() as temp:
            gate = Path(temp) / "window.vhgate"
            set_capture_gate(gate, True)
            self.assertEqual(gate.read_bytes(), MARKER)
            set_capture_gate(gate, False)
            self.assertFalse(gate.exists())

    def test_refuse_duplicate_activation(self):
        with tempfile.TemporaryDirectory() as temp:
            gate = Path(temp) / "window.vhgate"
            set_capture_gate(gate, True)
            with self.assertRaises(ValueError):
                set_capture_gate(gate, True)
            self.assertEqual(gate.read_bytes(), MARKER)

    def test_stop_closed_gate_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                set_capture_gate(Path(temp) / "missing.vhgate", False)

    def test_invalid_marker_never_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            gate = Path(temp) / "window.vhgate"
            gate.write_bytes(b"arbitrary")
            with self.assertRaises(ValueError):
                set_capture_gate(gate, False)
            self.assertEqual(gate.read_bytes(), b"arbitrary")

    def test_extension_absolute_path_and_boolean_enforced(self):
        with tempfile.TemporaryDirectory() as temp:
            for invalid in (Path("relative.vhgate"), Path(temp) / "bad.txt"):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    set_capture_gate(invalid, True)
            with self.assertRaises(ValueError):
                set_capture_gate(Path(temp) / "window.vhgate", 1)

    def test_symlink_never_followed_or_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            target = directory / "private"
            target.write_bytes(b"some-data")
            gate = directory / "window.vhgate"
            gate.symlink_to(target)
            with self.assertRaises(ValueError):
                set_capture_gate(gate, True)
            with self.assertRaises(ValueError):
                set_capture_gate(gate, False)
            self.assertEqual(target.read_bytes(), b"some-data")

    def test_gated_patch_refuses_repeat_or_wrong_source(self):
        patch = patch_gated_cdbase(SOURCE)
        with self.assertRaises(ValueError):
            patch_gated_cdbase(patch)
        with self.assertRaises(ValueError):
            patch_gated_cdbase(SOURCE.replace("ISOCDReadSectorFAD",
                                              "RandomReadFunction"))

    def test_gate_checks_exact_marker_content(self):
        patch = patch_gated_cdbase(SOURCE)
        self.assertIn("vh_first == '1' && vh_second == '\\n' && vh_third == EOF",
                      patch)
        self.assertIn('fopen(vh_gate_path, "rb")', patch)
        self.assertIn("VH_SATURN_CAPTURE_GATE", patch)
        self.assertNotIn("fwrite(vh_trace", patch)

    def test_patcher_preserves_crlf_newlines(self):
        patch = patch_gated_cdbase(SOURCE.replace("\n", "\r\n"))
        self.assertNotIn("\n", patch.replace("\r\n", ""))

    def test_fake_c_reads_window_during_one_process(self):
        cc = shutil.which("cc")
        if cc is None:
            self.skipTest("Host C compiler not available")
        # Fake program opens the gate between its first and second reads.
        calls = ("   ISOCDReadSectorFAD(160, b);\n"
                 "   ISOCDReadSectorFAD(170, b);\n"
                 "   ISOCDReadSectorFAD(999, b);")
        new_calls = ('   const char *gate = getenv("VH_SATURN_CAPTURE_GATE");\n'
                     "   ISOCDReadSectorFAD(160, b);\n"
                     '   FILE *g = fopen(gate, "wb");\n'
                     "   if (!g) return 2;\n"
                     '   fputs("1\\n", g);\n'
                     "   fclose(g);\n"
                     "   ISOCDReadSectorFAD(170, b);\n"
                     "   ISOCDReadSectorFAD(180, b);\n"
                     "   remove(gate);\n"
                     "   ISOCDReadSectorFAD(190, b);\n"
                     "   ISOCDReadSectorFAD(999, b);")
        self.assertIn(calls, SOURCE)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src, binary = root / "fabricated.c", root / "fabricated"
            output, gate = root / "trace.vhcdlog", root / "gate.vhgate"
            src.write_text(patch_gated_cdbase(SOURCE.replace(calls, new_calls)),
                           encoding="utf-8")
            build = subprocess.run([cc, "-std=c99", "-Wall", "-Wextra", str(src),
                                    "-o", str(binary)], capture_output=True,
                                   text=True, timeout=20)
            self.assertEqual(build.returncode, 0)
            env = dict(os.environ, VH_SATURN_FAD_LOG=str(output),
                       VH_SATURN_CAPTURE_GATE=str(gate))
            run = subprocess.run([str(binary)], env=env, capture_output=True,
                                 text=True, timeout=10)
            self.assertEqual(run.returncode, 0)
            self.assertEqual(output.read_text(encoding="ascii"),
                             "VHCD_FAD 170\nVHCD_FAD 180\n")
            self.assertFalse(gate.exists())

    def test_malformed_markers_never_log(self):
        cc = shutil.which("cc")
        if cc is None:
            self.skipTest("Host C compiler not available")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src, binary = root / "fabricated.c", root / "fabricated"
            output, gate = root / "trace.vhcdlog", root / "gate.vhgate"
            src.write_text(patch_gated_cdbase(SOURCE), encoding="utf-8")
            build = subprocess.run([cc, "-std=c99", str(src), "-o",
                                    str(binary)], capture_output=True,
                                   text=True, timeout=20)
            self.assertEqual(build.returncode, 0)
            env = dict(os.environ, VH_SATURN_FAD_LOG=str(output),
                       VH_SATURN_CAPTURE_GATE=str(gate))
            for invalid in (b"", b"1", b"1\r\n", b"0\n", b"1\nx"):
                gate.write_bytes(invalid)
                subprocess.run([str(binary)], env=env, check=True, timeout=10)
                self.assertFalse(output.exists())

    def test_missing_gate_environment_does_not_log(self):
        cc = shutil.which("cc")
        if cc is None:
            self.skipTest("Host C compiler not available")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src, binary = root / "fabricated.c", root / "fabricated"
            output = root / "trace.vhcdlog"
            src.write_text(patch_gated_cdbase(SOURCE), encoding="utf-8")
            build = subprocess.run([cc, "-std=c99", str(src), "-o",
                                    str(binary)], capture_output=True,
                                   text=True, timeout=20)
            self.assertEqual(build.returncode, 0)
            env = dict(os.environ, VH_SATURN_FAD_LOG=str(output))
            env.pop("VH_SATURN_CAPTURE_GATE", None)
            subprocess.run([str(binary)], env=env, check=True, timeout=10)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
