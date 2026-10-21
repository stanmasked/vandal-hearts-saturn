"""Stage66 tests for a provenance-linked, non-payload battle observation manifest."""
import unittest
from tools.saturn_battle_evidence import validate_document


def manifest():
    return {
        "schema_version": 1,
        "source": {
            "platform": "Sega Saturn",
            "product_code": "T-9526G",
            "release_label": "English v1.1 translation-patched",
            "capture_kind": "emulator",
        },
        "scene": {
            "label": "synthetic test scene",
            "width": 3,
            "height": 3,
            "coordinate_system": "x-right-y-down",
            "status": "partial",
        },
        "evidence": [{
            "id": "ev1", "kind": "screenshot",
            "artifact_ref": "private-ref:frame-001",
            "note": "synthetic fixture only",
        }],
        "cells": [{
            "x": 1, "y": 1, "terrain": None, "elevation": None,
            "movement_cost": None, "traversable": None,
            "confidence": "unknown", "evidence_ids": ["ev1"],
        }],
        "units": [{
            "id": "unit1", "team": "player", "class_label": None,
            "x": 1, "y": 1, "hp": 8, "max_hp": 10, "move_points": None,
            "confidence": "observed", "evidence_ids": ["ev1"],
        }],
        "observations": [{
            "id": "obs1", "kind": "position", "claim": "unit visible at test coordinate",
            "confidence": "observed", "evidence_ids": ["ev1"],
        }],
        "turns": [{
            "round": 1, "active_side": "player",
            "actions": [{
                "kind": "move", "actor_id": "unit1", "target_id": None,
                "from": {"x": 1, "y": 1}, "to": {"x": 2, "y": 1},
                "result": "synthetic action", "evidence_ids": ["ev1"],
            }],
        }],
    }


class SaturnBattleEvidenceTests(unittest.TestCase):
    def test_valid_partial_manifest_is_accepted_without_assuming_unknowns(self):
        report = validate_document(manifest())
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["summary"]["counts"]["cells"], 1)
        self.assertEqual(report["summary"]["unknown_counts"]["cell_terrain"], 1)
        self.assertEqual(report["summary"]["unknown_counts"]["unit_hp"], 0)

    def test_summary_does_not_echo_claims_or_private_artifact_refs(self):
        report = validate_document(manifest())
        serialized = str(report["summary"])
        self.assertNotIn("unit visible at test coordinate", serialized)
        self.assertNotIn("private-ref:frame-001", serialized)
        self.assertNotIn("synthetic action", serialized)

    def test_duplicate_cell_coordinate_is_rejected(self):
        data = manifest()
        data["cells"].append(dict(data["cells"][0]))
        report = validate_document(data)
        self.assertFalse(report["valid"])
        self.assertTrue(any("duplicate cell coordinate" in e for e in report["errors"]))

    def test_out_of_bounds_unit_is_rejected(self):
        data = manifest()
        data["units"][0]["x"] = 3
        report = validate_document(data)
        self.assertFalse(report["valid"])
        self.assertTrue(any("outside scene bounds" in e for e in report["errors"]))

    def test_hp_above_maximum_is_rejected(self):
        data = manifest()
        data["units"][0]["hp"] = 11
        report = validate_document(data)
        self.assertFalse(report["valid"])
        self.assertTrue(any("exceeds max_hp" in e for e in report["errors"]))

    def test_unknown_evidence_reference_is_rejected(self):
        data = manifest()
        data["cells"][0]["evidence_ids"] = ["missing"]
        report = validate_document(data)
        self.assertFalse(report["valid"])
        self.assertTrue(any("unknown evidence id" in e for e in report["errors"]))

    def test_private_artifact_ref_rejects_urls_and_paths(self):
        for bad in ("https://example.com/frame.png", "/tmp/frame.png",
                    "private-ref:../frame", "private-ref:"):
            with self.subTest(bad=bad):
                data = manifest()
                data["evidence"][0]["artifact_ref"] = bad
                self.assertFalse(validate_document(data)["valid"])

    def test_action_unit_references_must_exist(self):
        data = manifest()
        data["turns"][0]["actions"][0]["actor_id"] = "unknown"
        report = validate_document(data)
        self.assertFalse(report["valid"])
        self.assertTrue(any("unknown unit id" in e for e in report["errors"]))

    def test_overlapping_units_are_a_warning_not_silent_rewrite(self):
        data = manifest()
        other = dict(data["units"][0])
        other["id"] = "unit2"
        data["units"].append(other)
        report = validate_document(data)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["summary"]["overlap_warning_count"], 1)
        self.assertTrue(report["warnings"])

    def test_zero_size_scene_and_invalid_confidence_are_rejected(self):
        data = manifest()
        data["scene"]["width"] = 0
        data["cells"][0]["confidence"] = "certain"
        report = validate_document(data)
        self.assertFalse(report["valid"])
        self.assertTrue(any("scene.width" in e for e in report["errors"]))
        self.assertTrue(any("confidence" in e for e in report["errors"]))

    def test_unhashable_enum_values_and_boolean_schema_version_are_rejected(self):
        data = manifest()
        data["scene"]["status"] = ["partial"]
        report = validate_document(data)
        self.assertFalse(report["valid"])
        self.assertTrue(any("scene.status" in e for e in report["errors"]))
        data = manifest()
        data["schema_version"] = True
        self.assertFalse(validate_document(data)["valid"])

    def test_relative_elevation_accepts_signed_integer_but_not_boolean(self):
        data = manifest()
        data["cells"][0]["elevation"] = -3
        self.assertTrue(validate_document(data)["valid"])
        data["cells"][0]["elevation"] = True
        result = validate_document(data)
        self.assertFalse(result["valid"])
        self.assertTrue(any("elevation" in e for e in result["errors"]))

    def test_non_object_input_is_rejected(self):
        report = validate_document(["not", "a", "manifest"])
        self.assertFalse(report["valid"])
        self.assertEqual(report["errors"], ["$: expected object"])


if __name__ == "__main__":
    unittest.main()
