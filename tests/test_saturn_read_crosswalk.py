"""Stage73: private Saturn read crosswalk tests use only synthetic ISO extents."""
import unittest
from tools.saturn_read_crosswalk import crosswalk, ADDRESSING


def inventory():
    return {
        "file_entries": [
            {"name": "MAP_1_1C.BIN", "lba": 10, "bytes": 4096,
             "private_payload": "do not export"},
            {"name": "MAP_1_1P.BIN", "lba": 12, "bytes": 2048},
            {"name": "BATL1PRG.BIN", "lba": 20, "bytes": 4096},
            {"name": "BATLEPRG.BIN", "lba": 22, "bytes": 2048},
            {"name": "EV01.PRG", "lba": 30, "bytes": 2048},
            {"name": "EVENT01.DAT", "lba": 31, "bytes": 0},
            {"name": "M_MAP01.MAP", "lba": 40, "bytes": 4096},
            {"name": "OTHER.DAT", "lba": 50, "bytes": 2048},
        ],
        "operator_private_label": "must-not-appear",
    }


def trace():
    return {
        "schema_version": 1, "addressing": ADDRESSING,
        "private_path": "must-not-appear",
        "runs": [
            {"phase": "first_battle_entry",
             "reads": [
                 {"lba": 10, "sectors": 1},
                 {"lba": 10, "sectors": 2},
                 {"lba": 20, "sectors": 2},
                 {"lba": 40, "sectors": 1},
                 {"lba": 50, "sectors": 1},
             ]},
            {"phase": "menu_control",
             "reads": [
                 {"lba": 20, "sectors": 1},
                 {"lba": 30, "sectors": 1},
                 {"lba": 50, "sectors": 1},
             ]},
        ],
    }


def by_name(result):
    return {c["candidate_name"]: c for c in result["candidate_results"]}


class SaturnReadCrosswalkTests(unittest.TestCase):
    def test_battle_only_candidate_vs_shared_and_control_only(self):
        result = crosswalk(inventory(), trace())
        candidates = by_name(result)
        a = candidates["MAP_1_1C.BIN"]
        self.assertEqual(a["observation"], "observed_in_battle_only")
        self.assertEqual(a["battle_sectors"], 2)
        self.assertEqual(a["battle_exclusive_sectors"], 2)
        self.assertEqual(a["first_battle_runs_with_reads"], 1)
        b = candidates["BATL1PRG.BIN"]
        self.assertEqual(b["observation"], "observed_in_battle_and_control")
        self.assertEqual(b["battle_sectors"], 2)
        self.assertEqual(b["menu_sectors"], 1)
        self.assertEqual(b["battle_exclusive_sectors"], 1)
        self.assertEqual(candidates["EV01.PRG"]["observation"],
                         "observed_in_control_only")
        self.assertEqual(candidates["M_MAP01.MAP"]["battle_sectors"], 1)
        self.assertEqual(candidates["EVENT01.DAT"]["battle_sectors"], 0)
        self.assertFalse(result["first_battle_map_identified"])

    def test_sector_overlap_clips_to_file_extent(self):
        t = trace()
        t["runs"][0]["reads"] = [{"lba": 9, "sectors": 5}]
        a = by_name(crosswalk(inventory(), t))["MAP_1_1C.BIN"]
        self.assertEqual(a["battle_sectors"], 2)

    def test_duplicate_reads_do_not_double_count_union(self):
        t = trace()
        t["runs"][0]["reads"] *= 3
        a = by_name(crosswalk(inventory(), t))["MAP_1_1C.BIN"]
        self.assertEqual(a["battle_sectors"], 2)
        self.assertEqual(a["first_battle_runs_with_reads"], 1)

    def test_multiple_battle_runs_report_repeat_count(self):
        t = trace()
        t["runs"].insert(1, {
            "phase": "first_battle_entry",
            "reads": [{"lba": 10, "sectors": 1}],
        })
        a = by_name(crosswalk(inventory(), t))["MAP_1_1C.BIN"]
        self.assertEqual(a["first_battle_runs_with_reads"], 2)
        self.assertEqual(a["battle_sectors"], 2)

    def test_overlapping_iso_extents_cannot_claim_unambiguous_reads(self):
        i = inventory()
        i["file_entries"].append({"name": "ALIAS.BIN", "lba": 11, "bytes": 2048})
        a = by_name(crosswalk(i, trace()))["MAP_1_1C.BIN"]
        self.assertTrue(a["ambiguous_iso_extent"])
        self.assertEqual(a["observation"], "ambiguous_extent")

    def test_missing_candidate_not_guessed(self):
        i = inventory()
        i["file_entries"] = [e for e in i["file_entries"]
                             if e["name"] != "MAP_1_1C.BIN"]
        a = by_name(crosswalk(i, trace()))["MAP_1_1C.BIN"]
        self.assertEqual(a["observation"], "candidate_absent")
        self.assertFalse(a["present_in_iso"])

    def test_wrong_address_convention_fails_without_implicit_150_shift(self):
        for address in ("disc_physical_msf", "lba_plus_150", "", None):
            with self.subTest(address=address):
                t = trace()
                t["addressing"] = address
                with self.assertRaisesRegex(ValueError, "ISO9660 logical"):
                    crosswalk(inventory(), t)

    def test_control_capture_is_required_and_cannot_be_empty(self):
        t = trace()
        t["runs"] = [t["runs"][0]]
        with self.assertRaisesRegex(ValueError, "bounded menu-control"):
            crosswalk(inventory(), t)
        t = trace()
        t["runs"][1]["reads"] = []
        with self.assertRaisesRegex(ValueError, "needs sector-read"):
            crosswalk(inventory(), t)

    def test_invalid_numeric_lba_and_counts_fail_closed(self):
        for key, value in (("lba", -1), ("lba", True),
                           ("sectors", 0), ("sectors", False),
                           ("sectors", 20000001)):
            with self.subTest(key=key, value=value):
                t = trace()
                t["runs"][0]["reads"][0][key] = value
                with self.assertRaises(ValueError):
                    crosswalk(inventory(), t)

    def test_corrupted_iso_records_fail_closed(self):
        for change in (
            {"name": "../BAD.BIN"},
            {"lba": True}, {"bytes": -1},
            {"name": "MAP_1_1P.BIN"},
        ):
            with self.subTest(change=change):
                i = inventory()
                i["file_entries"][0].update(change)
                with self.assertRaises(ValueError):
                    crosswalk(i, trace())

    def test_no_private_media_identifiers_or_false_loader_proof_in_report(self):
        result = crosswalk(inventory(), trace())
        text = str(result)
        self.assertNotIn("must-not-appear", text)
        self.assertNotIn("do not export", text)
        self.assertNotIn("OTHER.DAT", text)
        self.assertNotIn("private_path", text)
        self.assertFalse(result["trace_origin_authenticated"])
        for item in result["candidate_results"]:
            self.assertFalse(item["loader_relationship_verified"])

    def test_control_overlap_subtraction_counts_sectors_not_event_calls(self):
        t = trace()
        t["runs"][1]["reads"] = [{"lba": 10, "sectors": 1},
                                  {"lba": 10, "sectors": 1},
                                  {"lba": 50, "sectors": 1}]
        a = by_name(crosswalk(inventory(), t))["MAP_1_1C.BIN"]
        self.assertEqual(a["battle_sectors"], 2)
        self.assertEqual(a["menu_sectors"], 1)
        self.assertEqual(a["battle_exclusive_sectors"], 1)


if __name__ == "__main__":
    unittest.main()
