"""Stage67: strictly synthetic battle reference coverage fixtures."""
import copy
import unittest

from tools.saturn_battle_coverage import assess_coverage


def fixture():
    cells = [
        {"x": x, "y": y, "terrain": "test-floor", "elevation": 0,
         "movement_cost": 1, "traversable": True, "confidence": "observed",
         "evidence_ids": ["ev-frame"]}
        for y in range(2) for x in range(2)
    ]
    units = [
        {"id": "ally", "team": "player", "class_label": None, "x": 0, "y": 0,
         "hp": 10, "max_hp": 10, "move_points": 3,
         "confidence": "observed", "evidence_ids": ["ev-frame"]},
        {"id": "foe", "team": "enemy", "class_label": None, "x": 1, "y": 1,
         "hp": 8, "max_hp": 8, "move_points": 2,
         "confidence": "observed", "evidence_ids": ["ev-frame"]},
    ]
    return {
        "schema_version": 1,
        "source": {"platform": "Sega Saturn", "product_code": "T-9526G",
                   "release_label": "synthetic test source", "capture_kind": "emulator"},
        "scene": {"label": "synthetic scene, NOT original first battle",
                  "width": 2, "height": 2, "coordinate_system": "x-right-y-down",
                  "status": "observed"},
        "evidence": [{"id": "ev-frame", "kind": "screenshot",
                      "artifact_ref": "private-ref:synthetic-frame"}],
        "cells": cells,
        "units": units,
        "observations": [
            {"id": kind, "kind": kind, "claim": "synthetic only",
             "confidence": "observed", "evidence_ids": ["ev-frame"]}
            for kind in ("movement", "attack", "turn_order", "victory")
        ],
        "turns": [
            {"round": 1, "active_side": "player", "actions": [
                {"kind": "move", "actor_id": "ally", "target_id": None,
                 "from": {"x": 0, "y": 0}, "to": {"x": 0, "y": 1},
                 "result": "synthetic", "evidence_ids": ["ev-frame"]},
                {"kind": "attack", "actor_id": "ally", "target_id": "foe",
                 "result": "synthetic", "evidence_ids": ["ev-frame"]}]}
        ],
    }


class BattleCoverageTests(unittest.TestCase):
    def test_synthetic_complete_cover_is_not_authenticity(self):
        result = assess_coverage(fixture())
        self.assertTrue(result["schema_valid"])
        self.assertTrue(result["coverage_complete"], result["blockers"])
        self.assertFalse(result["authenticity_verified"])
        self.assertFalse(result["native_battle_verified"])
        self.assertEqual(result["counts"]["expected_cells"], 4)

    def test_invalid_manifest_never_gets_a_complete_score(self):
        data = fixture()
        data["cells"].append(copy.deepcopy(data["cells"][0]))
        result = assess_coverage(data)
        self.assertFalse(result["schema_valid"])
        self.assertEqual(result["blockers"], ["INVALID_EVIDENCE_MANIFEST"])

    def test_incomplete_rectangle_is_blocked(self):
        data = fixture()
        data["cells"].pop()
        self.assertIn("GRID_COVERAGE_INCOMPLETE", assess_coverage(data)["blockers"])

    def test_unobserved_cell_is_blocked(self):
        data = fixture()
        data["cells"][0]["confidence"] = "inferred"
        self.assertIn("CELLS_REQUIRE_OBSERVED_VALUES_AND_EVIDENCE",
                      assess_coverage(data)["blockers"])

    def test_missing_terrain_or_height_is_blocked(self):
        for key in ("terrain", "elevation", "movement_cost", "traversable"):
            with self.subTest(key=key):
                data = fixture()
                data["cells"][0][key] = None
                self.assertFalse(assess_coverage(data)["coverage_complete"])

    def test_bad_roster_and_occupied_cell_blocked(self):
        data = fixture()
        # Preserve valid action references; only change the roster side.
        # Deleting the enemy would invalidate the Stage66 action target first.
        data["units"][1]["team"] = "player"
        self.assertIn("ROSTER_REQUIRES_BOTH_SIDES", assess_coverage(data)["blockers"])
        data = fixture()
        data["cells"][0]["traversable"] = False
        self.assertIn("UNIT_NOT_ON_CONFIRMED_WALKABLE_CELL",
                      assess_coverage(data)["blockers"])

    def test_unobserved_unit_stats_blocked(self):
        data = fixture()
        data["units"][0]["move_points"] = None
        self.assertIn("UNITS_REQUIRE_OBSERVED_STATS_AND_EVIDENCE",
                      assess_coverage(data)["blockers"])

    def test_overlap_blocks_even_if_stage66_warns_only(self):
        data = fixture()
        data["units"][1]["x"], data["units"][1]["y"] = 0, 0
        self.assertIn("UNIT_POSITIONS_OVERLAP", assess_coverage(data)["blockers"])

    def test_mechanics_observations_are_not_optional(self):
        data = fixture()
        data["observations"][0]["confidence"] = "unknown"
        self.assertIn("REQUIRED_MECHANICS_NOT_OBSERVED", assess_coverage(data)["blockers"])

    def test_actions_must_have_actor_and_evidence(self):
        data = fixture()
        data["turns"][0]["actions"][0]["evidence_ids"] = []
        self.assertIn("ACTION_TRACE_INCOMPLETE", assess_coverage(data)["blockers"])
        data = fixture()
        data["turns"][0]["actions"] = []
        self.assertIn("ACTION_TRACE_INCOMPLETE", assess_coverage(data)["blockers"])

    def test_inverted_round_numbers_blocked(self):
        data = fixture()
        data["turns"] = [{"round": 2, "active_side": "enemy",
                          "actions": [{"kind": "end_turn", "actor_id": "foe",
                                       "evidence_ids": ["ev-frame"]}]}
                         ] + data["turns"]
        self.assertIn("ROUND_ORDER_INCONSISTENT", assess_coverage(data)["blockers"])

    def test_terminal_observation_must_be_supported(self):
        data = fixture()
        data["observations"][-1]["confidence"] = "unknown"
        self.assertIn("TERMINAL_OUTCOME_NOT_OBSERVED",
                      assess_coverage(data)["blockers"])

    def test_attack_requires_target_and_action_type(self):
        data = fixture()
        data["turns"][0]["actions"] = data["turns"][0]["actions"][:1]
        self.assertIn("BATTLE_ACTION_TYPES_INCOMPLETE",
                      assess_coverage(data)["blockers"])
        data = fixture()
        data["turns"][0]["actions"][1]["target_id"] = None
        self.assertIn("ATTACK_TARGET_NOT_IDENTIFIED",
                      assess_coverage(data)["blockers"])

    def test_actor_must_match_turn_side(self):
        data = fixture()
        data["turns"][0]["active_side"] = "enemy"
        self.assertIn("ACTION_ACTOR_SIDE_MISMATCH",
                      assess_coverage(data)["blockers"])

    def test_counts_and_blockers_do_not_contain_private_labels(self):
        data = fixture()
        data["scene"]["label"] = "super secret scene label"
        data["source"]["release_label"] = "super secret source label"
        result = assess_coverage(data)
        self.assertNotIn("super secret", str(result))
        self.assertNotIn("private-ref:synthetic-frame", str(result))


if __name__ == "__main__":
    unittest.main()
