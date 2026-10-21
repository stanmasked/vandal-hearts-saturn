"""Stage76 synthetic C callback compilation and numeric Saturn CD trace tests."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.saturn_yabause_cdbase_hook import patch_cdbase
from tools.saturn_yabause_fad_log import build_private_trace, parse_fad_log
from tools.saturn_read_repetition import analyze_repeatability
from test_saturn_read_crosswalk import inventory

# A fabricated callback, not original Yabause implementation or Saturn code.
SOURCE = r'''#include <stdio.h>
#include <stdlib.h>
typedef unsigned int u32;
static int ISOCDReadSectorFAD(u32 FAD, void *buffer) {
   size_t num_read = 0;
   if (FAD != 999) {
      FILE *f = tmpfile();
      if (!f) return 0;
      fputc('x', f);
      rewind(f);
      num_read = fread(buffer, 1, 1, f);
      fclose(f);
   }
   return 1;
}
static void ISOCDReadAheadFAD(void) {
}
int main(void) {
   char b[32] = {0};
   ISOCDReadSectorFAD(160, b);
   ISOCDReadSectorFAD(170, b);
   ISOCDReadSectorFAD(999, b);
   return 0;
}
'''


def logs():
    return [
        ("first_battle_entry", "VHCD_FAD 160\nVHCD_FAD 170\n"),
        ("first_battle_entry", "VHCD_FAD 160\nVHCD_FAD 170\n"),
        ("menu_control", "VHCD_FAD 170\n"),
        ("menu_control", "VHCD_FAD 170\n"),
    ]


class YabauseCaptureAdapterTests(unittest.TestCase):
    def test_patcher_adds_one_success_only_hook(self):
        result = patch_cdbase(SOURCE)
        self.assertEqual(result.count("VH_SATURN_FAD_LOG"), 1)
        self.assertIn("if (num_read > 0)", result)
        self.assertIn('fprintf(vh_trace, "VHCD_FAD %u\\n"', result)
        self.assertEqual(result.count("static int ISOCDReadSectorFAD("), 1)

    def test_patcher_rejects_wrong_source_and_double_instrumentation(self):
        for bad in (SOURCE.replace("ISOCDReadSectorFAD", "DummyCDReadSectorFAD"),
                    SOURCE.replace("fread(", "fwrite("),
                    SOURCE.replace("static void ISOCDReadAheadFAD", "void missing"),
                    patch_cdbase(SOURCE)):
            with self.subTest(source=bad[-35:]), self.assertRaises(ValueError):
                patch_cdbase(bad)

    def test_preserves_crlf(self):
        changed = patch_cdbase(SOURCE.replace("\n", "\r\n"))
        self.assertNotIn("\n", changed.replace("\r\n", ""))

    def test_compiled_fabricated_callback_emits_only_successes(self):
        cc = shutil.which("cc")
        if cc is None:
            self.skipTest("No host C compiler")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "fake.c"
            binary = root / "fake"
            trace = root / "local.vhcdlog"
            source.write_text(patch_cdbase(SOURCE), encoding="utf-8")
            compiled = subprocess.run(
                [cc, "-std=c99", "-Wall", "-Wextra", str(source), "-o", str(binary)],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(compiled.returncode, 0, "fabricated C callback compile")
            env = dict(os.environ, VH_SATURN_FAD_LOG=str(trace))
            run = subprocess.run([str(binary)], env=env, capture_output=True,
                                 text=True, timeout=10)
            self.assertEqual(run.returncode, 0)
            self.assertEqual(trace.read_text(encoding="ascii"),
                             "VHCD_FAD 160\nVHCD_FAD 170\n")
            trace.unlink()
            env.pop("VH_SATURN_FAD_LOG")
            subprocess.run([str(binary)], env=env, check=True, timeout=10)
            self.assertFalse(trace.exists())

    def test_four_capture_numeric_pipeline(self):
        result = build_private_trace(1000, logs())
        self.assertEqual(len(result["runs"]), 4)
        self.assertEqual(result["runs"][0]["reads"][0],
                         {"lba": 10, "sectors": 1})
        self.assertEqual(result["runs"][2]["reads"][0],
                         {"lba": 20, "sectors": 1})
        report = analyze_repeatability(inventory(), result)
        self.assertTrue(report["numeric_repetition_gate_ready"])
        found = {x["candidate_name"]: x for x in report["results"]}
        self.assertEqual(found["MAP_1_1C.BIN"]["common_battle_not_in_any_menu"], 1)
        self.assertFalse(report["first_battle_map_identified"])

    def test_numeric_line_validation(self):
        self.assertEqual(parse_fad_log("VHCD_FAD 160\n"),
                         [{"fad": 160, "sectors": 1}])
        for bad in ("", "VHCD_FAD -1\n", "VHCD_FAD 01\n",
                    "VHCD_FAD 160 path=/secret\n", "original game image data",
                    "VHCD_FAD 160\n\n", "VHCD_FAD 160\nVHCD_FAD x"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_fad_log(bad)

    def test_track_two_and_lead_in_rejected(self):
        for fad in (149, 1150):
            samples = logs()
            samples[0] = ("first_battle_entry", "VHCD_FAD " + str(fad) + "\n")
            with self.subTest(fad=fad), self.assertRaises(ValueError):
                build_private_trace(1000, samples)

    def test_missing_phase_rejected(self):
        for subset in (logs()[:3], logs()[1:], logs()[:2]):
            with self.subTest(n=len(subset)), self.assertRaises(ValueError):
                build_private_trace(1000, subset)

    def test_bounds_and_session_info_not_fabricated(self):
        with self.assertRaises(ValueError):
            build_private_trace(True, logs())
        result = build_private_trace(1000, logs())
        self.assertEqual(result["addressing"], "iso9660_logical_data_lba")
        self.assertNotIn("capture_independence_verified", result)
        self.assertNotIn("/secret", str(result))

    def test_excessive_events_rejected(self):
        with self.assertRaises(ValueError):
            parse_fad_log("VHCD_FAD 160\n" * 20001)

    def test_patch_never_logs_buffer_content(self):
        patched = patch_cdbase(SOURCE)
        self.assertNotIn("fwrite(vh_trace", patched)
        self.assertEqual(patched.count("VHCD_FAD %u"), 1)


if __name__ == "__main__":
    unittest.main()
