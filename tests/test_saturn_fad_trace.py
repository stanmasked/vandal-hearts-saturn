"""Stage73 FAD conversion tests use fabricated ranges, never Saturn media."""
import unittest

from tools.saturn_fad_trace import convert_fad_trace, FAD_ADDRESSING
from tools.saturn_read_crosswalk import crosswalk, ADDRESSING
from test_saturn_read_crosswalk import inventory


def fad_fixture():
    return {
        "schema_version": 1, "addressing": FAD_ADDRESSING,
        "private_disc_path": "must-not-leak",
        "runs": [
            {"phase": "first_battle_entry",
             "reads": [{"fad": 160, "sectors": 2},
                       {"fad": 170, "sectors": 1}]},
            {"phase": "menu_control",
             "reads": [{"fad": 170, "sectors": 1}]},
        ],
    }


class SaturnFadTraceTests(unittest.TestCase):
    def test_explicit_150_sector_conversion_and_crosswalk(self):
        result = convert_fad_trace(fad_fixture(), 500)
        self.assertEqual(result["addressing"], ADDRESSING)
        self.assertEqual(result["runs"][0]["reads"][0],
                         {"lba": 10, "sectors": 2})
        matched = crosswalk(inventory(), result)
        found = {c["candidate_name"]: c for c in matched["candidate_results"]}
        self.assertEqual(found["MAP_1_1C.BIN"]["battle_sectors"], 2)
        self.assertEqual(found["BATL1PRG.BIN"]["menu_sectors"], 1)
        self.assertFalse(matched["first_battle_map_identified"])

    def test_conversion_never_infers_addressing(self):
        for label in (None, ADDRESSING, "physical_msf", ""):
            with self.subTest(label=label):
                t = fad_fixture()
                t["addressing"] = label
                with self.assertRaisesRegex(ValueError, "explicitly labeled"):
                    convert_fad_trace(t, 500)

    def test_lead_in_and_track_two_cannot_be_silently_mapped(self):
        for fad, sectors in ((149, 1), (150, 0), (649, 2),
                             (650, 1), (True, 1), (150, True)):
            with self.subTest(fad=fad, sectors=sectors):
                t = fad_fixture()
                t["runs"][0]["reads"][0] = {"fad": fad, "sectors": sectors}
                with self.assertRaises(ValueError):
                    convert_fad_trace(t, 500)

    def test_track_length_must_be_bounded_integer(self):
        for length in (0, True, 500.0, -1, 20000001):
            with self.subTest(length=length), self.assertRaises(ValueError):
                convert_fad_trace(fad_fixture(), length)

    def test_conversion_does_not_copy_untrusted_private_fields(self):
        result = convert_fad_trace(fad_fixture(), 500)
        self.assertNotIn("must-not-leak", str(result))
        self.assertNotIn("private_disc_path", str(result))
        self.assertEqual(set(result), {"schema_version", "addressing", "runs"})

    def test_empty_menu_capture_still_fails_closed(self):
        t = fad_fixture()
        t["runs"][1]["reads"] = []
        with self.assertRaisesRegex(ValueError, "needs sector-read"):
            convert_fad_trace(t, 500)


if __name__ == "__main__":
    unittest.main()
