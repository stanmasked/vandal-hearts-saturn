"""Stage91 CUE runtime hardening contracts, invented files only."""
import unittest

from tools.patch_yabause_strict_split_cue import (
    patch_strict_split_cue, STRICT_LOOP,
)
from tools.verify_yabause_strict_cue import invalid_cue_variants
from tools.verify_yabause_split_cue import make_split_fixture
import tempfile
from pathlib import Path


class StrictCueParserTests(unittest.TestCase):
    def test_invalid_unpinned_original_source_is_rejected(self):
        for b in (b"", b"fake" * 15000, b"LoadBinCue" * 6000):
            with self.subTest(size=len(b)), self.assertRaises(ValueError):
                patch_strict_split_cue(b)

    def test_grammar_bounds_and_escape_rejection(self):
        for invariant in (
            "directive > 8", "directive != 8",
            "line[length - 1] != '\\n'", "length >= sizeof(line) - 1",
            '"CATALOG "', "p[k] < '0' || p[k] > '9'",
            'strcmp(p, "TRACK 01 MODE1/2352")',
            'strcmp(p, "TRACK 02 AUDIO")',
            'strcmp(p, "INDEX 01 00:02:00")',
            "strstr(name, \"..\")", "strpbrk(name, \"/\\\\:\")",
            "used < 0", "used != strlen",
        ):
            # Some spelled assertions correspond to suffixes of a typed cast;
            # don't require exact whitespace/parenthesization.
            if invariant == "used != strlen":
                self.assertIn("(size_t)used != strlen(p)", STRICT_LOOP)
            else:
                self.assertIn(invariant, STRICT_LOOP)

    def test_twelve_independent_invented_negative_cues(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, _ = make_split_fixture(root)
            original = Path(manifest["files"]["cue"]).read_bytes()
            cases = invalid_cue_variants(original)
            self.assertEqual(len(cases), 12)
            self.assertEqual(len(set(cases.values())), 12)
            self.assertTrue(original.startswith(b"CATALOG "))
            self.assertTrue(all(c != original for c in cases.values()))

    def test_pinned_parser_still_makes_no_media_claims(self):
        self.assertNotIn("Vandal Hearts", STRICT_LOOP)
        self.assertNotIn("CATALOG 123", STRICT_LOOP)
        self.assertNotIn("ISOCD.ReadSectorFAD", STRICT_LOOP)


if __name__ == "__main__":
    unittest.main()
