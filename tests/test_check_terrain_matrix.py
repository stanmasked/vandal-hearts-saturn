"""Stage71 small synthetic tests; CI separately invokes the compiled C++ probe."""
import unittest

from tools.check_terrain_matrix import (
    CASES, independent_aggregates, invented_cell, make_case,
)
from tools.saturn_battle_coverage import assess_coverage
from tools.saturn_terrain_bridge import export_numeric_terrain


class SyntheticTerrainMatrixTests(unittest.TestCase):
    def test_relative_height_sign_and_canonical_width(self):
        doc = make_case(3, 5)
        elevations = [cell["elevation"] for cell in doc["cells"]]
        self.assertTrue(any(v < 0 for v in elevations))
        self.assertTrue(any(v >= 0 for v in elevations))
        self.assertTrue(export_numeric_terrain(doc).startswith(
            "VH_TERRAIN_UNVERIFIED_V1\nSIZE 3 5\n"
        ))

    def test_all_cases_have_two_nonoverlapping_walkable_units(self):
        for w, h in CASES:
            with self.subTest(size=(w, h)):
                doc = make_case(w, h)
                self.assertNotEqual(
                    (doc["units"][0]["x"], doc["units"][0]["y"]),
                    (doc["units"][1]["x"], doc["units"][1]["y"]),
                )
                self.assertTrue(assess_coverage(doc)["coverage_complete"])
                self.assertEqual(len(doc["cells"]), w * h)

    def test_aggregate_is_independent_of_serialization(self):
        doc = make_case(2, 2)
        doc["cells"].reverse()
        self.assertEqual(independent_aggregates(2, 2)[2], 4)
        self.assertEqual(
            export_numeric_terrain(doc).splitlines()[2].split()[:3],
            ["CELL", "0", "0"],
        )

    def test_dimension_overflow_fails_closed(self):
        for w, h in ((129, 1), (1, 129), (1, 1), (0, 5)):
            with self.subTest(size=(w, h)), self.assertRaises(ValueError):
                make_case(w, h)

    def test_elevation_boolean_does_not_bypass_validator(self):
        doc = make_case(2, 2)
        doc["cells"][0]["elevation"] = True
        with self.assertRaises(ValueError):
            export_numeric_terrain(doc)


if __name__ == "__main__":
    unittest.main()
