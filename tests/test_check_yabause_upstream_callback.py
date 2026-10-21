"""Stage78: public upstream source pinning and real-callback harness tests.

Unit tests use only invented source. GitHub Actions additionally downloads
Yabause's fixed public commit and compiles the actual callback.
"""
import unittest

from test_saturn_yabause_capture import SOURCE
from tools.check_yabause_upstream_callback import (
    UPSTREAM_BLOB, UPSTREAM_COMMIT, git_blob_sha,
    validate_upstream_source, extract_patched_callback, extract_primary_read_callback, harness,
)


class PinnedUpstreamCallbackTests(unittest.TestCase):
    def test_known_git_blob_formula(self):
        self.assertEqual(git_blob_sha(b"hello"),
                         "b6fc4c620b67d95f953a5c1c1230aaab5db5a1b0")
        with self.assertRaises(TypeError):
            git_blob_sha("hello")

    def test_pin_uses_full_immutable_git_ids(self):
        self.assertEqual(len(UPSTREAM_COMMIT), 40)
        self.assertEqual(len(UPSTREAM_BLOB), 40)
        self.assertNotEqual(UPSTREAM_COMMIT, UPSTREAM_BLOB)
        for value in (UPSTREAM_COMMIT, UPSTREAM_BLOB):
            self.assertEqual(set(value) <= set("0123456789abcdef"), True)

    def test_unpinned_or_invalid_source_is_rejected(self):
        for invalid in (b"", b"fake source", b"x" * 160001, False):
            with self.subTest(length=len(invalid) if hasattr(invalid, "__len__") else -1):
                with self.assertRaises((ValueError, TypeError)):
                    validate_upstream_source(invalid)

    def test_extract_from_fabricated_callback_only(self):
        callback = extract_patched_callback(SOURCE)
        self.assertIn("static int ISOCDReadSectorFAD", callback)
        self.assertIn("VH_SATURN_CAPTURE_GATE", callback)
        self.assertIn("vh_third == EOF", callback)
        self.assertNotIn("static void ISOCDReadAheadFAD", callback)
        self.assertNotIn("int main(void)", callback)
        self.assertEqual(callback.count("VHCD_FAD %u"), 1)

    def test_fake_harness_has_no_original_media_and_compiles_separately(self):
        callback = extract_patched_callback(SOURCE)
        code = harness(callback)
        self.assertIn("synthetic raw sectors", code.lower().replace("fabricated", "synthetic"))
        self.assertIn("num_read > 0", code)
        self.assertIn("VH_UPSTREAM_ISO_CALLBACK_TEST_PASS", code)
        self.assertNotIn("original_assets/", code)
        with self.assertRaises(ValueError):
            harness("not a callback")

    def test_repeat_instrumentation_fails_closed(self):
        from tools.saturn_yabause_gated_hook import patch_gated_cdbase
        modified = patch_gated_cdbase(SOURCE)
        with self.assertRaises(ValueError):
            extract_patched_callback(modified)


    def test_stage79_rejects_incomplete_primary_read_layout(self):
        with self.assertRaises(ValueError):
            extract_primary_read_callback(SOURCE)

    @staticmethod
    def invented_multimode_callback():
        # Synthetic C text: purely a string-shape fixture, never compiled.
        lines = (
            "   num_read = fread(buffer, 2352, 1, track->fp);\n" * 3 +
            "   num_read = fread(buffer, 2448, 1, track->fp);\n" +
            "   num_read = fread((char *)buffer + 0x10, 2048, 1, track->fp);\n"
        )
        return SOURCE.replace("   return 1;", lines + "   return 1;")

    def test_stage79_separately_tracks_primary_reads(self):
        modified = extract_primary_read_callback(self.invented_multimode_callback())
        self.assertIn("size_t vh_primary_read = 0;", modified)
        self.assertIn("if (vh_primary_read == 1)", modified)
        self.assertNotIn("if (num_read > 0)", modified)
        self.assertEqual(modified.count("vh_primary_read = (num_read = fread("), 5)
        self.assertIn("num_read = fread(buffer, 2352, 1, track->fp)", modified)

    def test_stage79_refuses_read_layout_drift(self):
        original = self.invented_multimode_callback()
        for changed in (
            original.replace("fread(buffer, 2448, 1, track->fp)", "fread(buffer, 2448, 2, track->fp)"),
            original.replace("fread(buffer, 2352, 1, track->fp)", "fread(buffer, 2352, 2, track->fp)", 1),
        ):
            with self.subTest(changed=changed[-60:]), self.assertRaises(ValueError):
                extract_primary_read_callback(changed)


if __name__ == "__main__":
    unittest.main()
