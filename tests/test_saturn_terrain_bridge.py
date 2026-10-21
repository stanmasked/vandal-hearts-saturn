"""Stage68 native terrain bridge; all input is a fabricated 2x2 test."""
import copy
import unittest

from test_saturn_battle_coverage import fixture
from tools.saturn_terrain_bridge import export_numeric_terrain, HEADER


class TerrainBridgeTests(unittest.TestCase):
    def test_exact_stable_row_major_numeric_export(self):
        doc = fixture()
        doc["cells"].reverse()
        doc["cells"][1]["movement_cost"] = 2
        result = export_numeric_terrain(doc)
        self.assertEqual(result,
            HEADER + "\nSIZE 2 2\n"
            "CELL 0 0 0 1 1\n"
            "CELL 1 0 0 1 1\n"
            "CELL 0 1 0 2 1\n"
            "CELL 1 1 0 1 1\n")
        self.assertNotIn("T-9526G", result)
        self.assertNotIn("synthetic", result)
        self.assertNotIn("private-ref", result)

    def test_unobserved_grid_rejected(self):
        doc = fixture()
        doc["cells"][0]["confidence"] = "inferred"
        with self.assertRaisesRegex(ValueError, "coverage incomplete"):
            export_numeric_terrain(doc)

    def test_undocumented_unit_or_missing_victory_rejected(self):
        doc = fixture()
        doc["units"][0]["move_points"] = None
        with self.assertRaises(ValueError):
            export_numeric_terrain(doc)
        doc = fixture()
        doc["observations"][-1]["evidence_ids"] = []
        with self.assertRaises(ValueError):
            export_numeric_terrain(doc)

    def test_native_safety_ranges_rejected_without_truncation(self):
        for field, bad in (("elevation", 100001), ("movement_cost", 100001)):
            with self.subTest(field=field):
                doc = fixture()
                doc["cells"][0][field] = bad
                with self.assertRaisesRegex(ValueError, "outside native bridge range"):
                    export_numeric_terrain(doc)

    def test_incomplete_json_schema_rejected_before_serialization(self):
        doc = fixture()
        del doc["cells"][0]["x"]
        with self.assertRaisesRegex(ValueError, "coverage incomplete"):
            export_numeric_terrain(doc)


if __name__ == "__main__":
    unittest.main()
