"""Stage78: public upstream source pinning and real-callback harness tests.

Unit tests use only invented source. GitHub Actions additionally downloads
Yabause's fixed public commit and compiles the actual callback.
"""
import unittest

from test_saturn_yabause_capture import SOURCE
from tools.check_yabause_upstream_callback import (
    UPSTREAM_BLOB, UPSTREAM_COMMIT, git_blob_sha,
    validate_upstream_source, extract_patched_callback, harness,
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


if __name__ == "__main__":
    unittest.main()
