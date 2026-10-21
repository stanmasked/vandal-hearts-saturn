"""Stage69 pure-Python tests of independent synthetic protocol logic."""
import unittest
from tools.check_terrain_bridge import synthetic_manifest, parse_receipt
from tools.saturn_battle_coverage import assess_coverage
from tools.saturn_terrain_bridge import export_numeric_terrain


class CrossLanguageTerrainContractTests(unittest.TestCase):
    def test_fabricated_manifest_is_coverage_complete_not_authentic(self):
        doc = synthetic_manifest()
        audit = assess_coverage(doc)
        self.assertTrue(audit["coverage_complete"], audit["blockers"])
        self.assertFalse(audit["authenticity_verified"])
        self.assertFalse(audit["native_battle_verified"])

    def test_exact_reference_terrain_serialization(self):
        data = export_numeric_terrain(synthetic_manifest())
        self.assertEqual(
            data,
            "VH_TERRAIN_UNVERIFIED_V1\nSIZE 2 2\n"
            "CELL 0 0 0 1 1\nCELL 1 0 1 2 1\n"
            "CELL 0 1 0 1 0\nCELL 1 1 0 1 1\n",
        )

    def test_rejects_invalid_native_receipts(self):
        with self.assertRaisesRegex(ValueError, "unexpected"):
            parse_receipt("anything")
        with self.assertRaisesRegex(ValueError, "unexpected units"):
            parse_receipt(
                "VH_TERRAIN_PROBE size=2x2 cells=4 walkable=3 "
                "blocked=1 cost_sum=5 elevation_sum=1 units=1"
            )
        with self.assertRaisesRegex(ValueError, "impossible native"):
            parse_receipt(
                "VH_TERRAIN_PROBE size=2x2 cells=4 walkable=3 "
                "blocked=3 cost_sum=5 elevation_sum=1 units=0"
            )

    def test_reference_receipt(self):
        self.assertEqual(
            parse_receipt(
                "VH_TERRAIN_PROBE size=2x2 cells=4 walkable=3 "
                "blocked=1 cost_sum=5 elevation_sum=1 units=0"
            ),
            (2, 2, 4, 3, 1, 5, 1, 0),
        )


if __name__ == "__main__":
    unittest.main()
