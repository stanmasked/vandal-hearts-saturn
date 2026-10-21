"""Stage74 synthetic-only per-sector repeatability, not real Saturn observations."""
import unittest

from test_saturn_read_crosswalk import inventory, trace
from tools.saturn_read_repetition import (
    _common_sectors, _intersect_sorted, analyze_repeatability,
)


def repeated_trace():
    t = trace()
    t["runs"] = [
        {"phase": "first_battle_entry",
         "reads": [{"lba": 10, "sectors": 2},
                   {"lba": 20, "sectors": 2},
                   {"lba": 40, "sectors": 1}]},
        {"phase": "first_battle_entry",
         "reads": [{"lba": 10, "sectors": 2},
                   {"lba": 20, "sectors": 2},
                   {"lba": 40, "sectors": 1}]},
        {"phase": "menu_control",
         "reads": [{"lba": 20, "sectors": 1}, {"lba": 30, "sectors": 1}]},
        {"phase": "menu_control",
         "reads": [{"lba": 20, "sectors": 1}, {"lba": 30, "sectors": 1}]},
    ]
    return t


def by_name(report):
    return {x["candidate_name"]: x for x in report["results"]}


class RepeatabilityTests(unittest.TestCase):
    def test_two_battle_and_two_menu_runs_yield_unverified_candidate(self):
        result = analyze_repeatability(inventory(), repeated_trace())
        self.assertTrue(result["numeric_repetition_gate_ready"])
        a = by_name(result)["MAP_1_1C.BIN"]
        self.assertEqual(a["status"], "repeated_battle_differential_candidate_only")
        self.assertEqual(a["common_battle_sectors"], 2)
        self.assertEqual(a["common_battle_not_in_any_menu"], 2)
        self.assertFalse(a["runtime_loader_verified"])
        self.assertFalse(result["capture_independence_verified"])

    def test_same_file_and_sector_in_control_does_not_claim_exclusivity(self):
        result = analyze_repeatability(inventory(), repeated_trace())
        batl = by_name(result)["BATL1PRG.BIN"]
        self.assertEqual(batl["common_battle_sectors"], 2)
        self.assertEqual(batl["common_battle_not_in_any_menu"], 1)
        t = repeated_trace()
        t["runs"][-1]["reads"].append({"lba": 21, "sectors": 1})
        # Menu control UNION covers two sectors, even across different runs.
        diff = by_name(analyze_repeatability(inventory(), t))["BATL1PRG.BIN"]
        self.assertEqual(diff["common_battle_not_in_any_menu"], 0)
        self.assertEqual(diff["status"], "all_repeated_sectors_seen_in_menu_controls")

    def test_duplicate_read_calls_not_counted_as_multiple_runs(self):
        t = repeated_trace()
        t["runs"] = [t["runs"][0], t["runs"][2]]
        t["runs"][0]["reads"] *= 6
        report = analyze_repeatability(inventory(), t)
        self.assertFalse(report["numeric_repetition_gate_ready"])
        a = by_name(report)["MAP_1_1C.BIN"]
        self.assertEqual(a["status"], "insufficient_repeated_capture_runs")
        self.assertEqual(a["battle_runs_with_candidate"], 1)

    def test_battle_runs_different_sectors_do_not_count_as_reproduced(self):
        t = repeated_trace()
        t["runs"][0]["reads"] = [{"lba": 10, "sectors": 1}]
        t["runs"][1]["reads"] = [{"lba": 11, "sectors": 1}]
        a = by_name(analyze_repeatability(inventory(), t))["MAP_1_1C.BIN"]
        self.assertEqual(a["battle_runs_with_candidate"], 2)
        self.assertEqual(a["common_battle_sectors"], 0)
        self.assertEqual(a["status"], "no_sector_common_to_all_battle_runs")

    def test_one_missing_battle_observation_suppresses_repetition(self):
        t = repeated_trace()
        t["runs"][1]["reads"] = [{"lba": 30, "sectors": 1}]
        a = by_name(analyze_repeatability(inventory(), t))["MAP_1_1C.BIN"]
        self.assertEqual(a["battle_runs_with_candidate"], 1)
        self.assertEqual(a["common_battle_not_in_any_menu"], 0)

    def test_ambiguous_iso_extent_never_promoted(self):
        inv = inventory()
        inv["file_entries"].append({"name": "ALIAS.BIN", "lba": 11, "bytes": 2048})
        a = by_name(analyze_repeatability(inv, repeated_trace()))["MAP_1_1C.BIN"]
        self.assertTrue(a["overlapping_iso_extents"])
        self.assertEqual(a["status"], "ambiguous_iso_extent")

    def test_candidate_absent_and_zero_length_do_not_generate_reads(self):
        inv = inventory()
        inv["file_entries"] = [f for f in inv["file_entries"]
                               if f["name"] != "MAP_1_1P.BIN"]
        result = by_name(analyze_repeatability(inv, repeated_trace()))
        self.assertEqual(result["MAP_1_1P.BIN"]["status"], "candidate_absent")
        self.assertEqual(result["EVENT01.DAT"]["common_battle_sectors"], 0)

    def test_interval_intersection_multiple_regions_and_touching_boundaries(self):
        first = [[0, 3], [5, 10], [15, 16]]
        second = [[2, 6], [8, 10], [16, 20]]
        self.assertEqual(_intersect_sorted(first, second),
                         [[2, 3], [5, 6], [8, 10]])
        self.assertEqual(_common_sectors([first, second, [[5, 11]]]),
                         [[5, 6], [8, 10]])

    def test_multiple_controls_cover_different_parts_of_repeated_sector(self):
        t = repeated_trace()
        t["runs"][-2]["reads"] = [{"lba": 10, "sectors": 1}]
        t["runs"][-1]["reads"] = [{"lba": 11, "sectors": 1}]
        a = by_name(analyze_repeatability(inventory(), t))["MAP_1_1C.BIN"]
        self.assertEqual(a["menu_runs_with_candidate"], 2)
        self.assertEqual(a["common_battle_not_in_any_menu"], 0)

    def test_duplicate_submitted_runs_are_not_claimed_independent(self):
        t = repeated_trace()
        t["private_run_label"] = "very private"
        report = analyze_repeatability(inventory(), t)
        self.assertTrue(report["numeric_repetition_gate_ready"])
        self.assertFalse(report["capture_independence_verified"])
        self.assertFalse(report["control_window_completeness_verified"])
        self.assertFalse(report["first_battle_map_identified"])
        self.assertNotIn("very private", str(report))
        self.assertNotIn("do not export", str(report))
        self.assertNotIn("must-not-appear", str(report))

    def test_requirements_cannot_be_boolean_or_out_of_range(self):
        for b, c in ((True, 2), (2, False), (1, 2), (2, 9), (0, -1)):
            with self.subTest(battle=b, menu=c), self.assertRaises(ValueError):
                analyze_repeatability(inventory(), repeated_trace(),
                                      min_battle=b, min_control=c)

    def test_invalid_addressing_and_unsafe_trace_fail_closed(self):
        t = repeated_trace()
        t["addressing"] = "saturn_cd_block_fad"
        with self.assertRaisesRegex(ValueError, "logical"):
            analyze_repeatability(inventory(), t)
        t = repeated_trace()
        t["runs"][1]["reads"][0]["lba"] = True
        with self.assertRaises(ValueError):
            analyze_repeatability(inventory(), t)

    def test_menu_control_phase_missing_is_never_ready(self):
        t = repeated_trace()
        t["runs"] = t["runs"][:2]
        with self.assertRaises(ValueError):
            analyze_repeatability(inventory(), t)

    def test_minimum_three_runs_requires_three_of_each(self):
        t = repeated_trace()
        self.assertFalse(analyze_repeatability(
            inventory(), t, min_battle=3, min_control=3)["numeric_repetition_gate_ready"])
        t["runs"].insert(1, t["runs"][0])
        t["runs"].append(t["runs"][-1])
        result = analyze_repeatability(inventory(), t, min_battle=3, min_control=3)
        self.assertTrue(result["numeric_repetition_gate_ready"])


if __name__ == "__main__":
    unittest.main()
