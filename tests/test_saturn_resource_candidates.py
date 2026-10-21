"""Stage17 tests for the metadata-only Saturn resource crosswalk."""
import unittest
from tools.saturn_resource_candidates import analyze_entries


def fixture_entries():
    entries = [
        {"name": "MAP_1_1C.BIN", "lba": 76336, "bytes": 84480, "payload": "must-not-export"},
        {"name": "MAP_1_1P.BIN", "lba": 76378, "bytes": 512},
        {"name": "BATL1PRG.BIN", "lba": 2329, "bytes": 245760},
        {"name": "BATLEPRG.BIN", "lba": 2449, "bytes": 245760},
        {"name": "EV01.PRG", "lba": 15972, "bytes": 13664},
        {"name": "EVENT01.DAT", "lba": 16669, "bytes": 1510},
    ]
    entries += [{"name": f"M_MAP{i:02d}.MAP", "lba": 100000 + i*84,
                 "bytes": 170624} for i in range(1, 35)]
    entries += [{"name": f"M_IVE{i:02d}.MAP", "lba": 104000 + i*84,
                 "bytes": 170624} for i in range(1, 23)]
    entries += [{"name": f"M_KEY{i:02d}.MAP", "lba": 108000 + i*84,
                 "bytes": 170624} for i in range(1, 18)]
    entries += [{"name": "M_SHOW.MAP", "lba": 112000, "bytes": 170624}]
    return entries


class SaturnResourceCandidatesTests(unittest.TestCase):
    def test_candidate_groups_and_contiguous_extents(self):
        report = analyze_entries(fixture_entries(), product_code="T-9526G",
                                 volume_id="VANDAL_HEARTS",
                                 source_label="synthetic fixture")
        groups = {g["group"]: g for g in report["candidate_groups"]}
        self.assertTrue(groups["numbered_scene_assets_1_1"]["extents_contiguous_in_iso"])
        self.assertTrue(groups["battle_program_candidates"]["extents_contiguous_in_iso"])
        self.assertFalse(groups["event_index_01_candidates"]["extents_contiguous_in_iso"])
        self.assertFalse(groups["numbered_scene_assets_1_1"]["runtime_relationship_verified"])
        self.assertEqual(groups["map_index_01_candidate"]["present_files"][0]["name"], "M_MAP01.MAP")

    def test_full_map_family_counts_are_metadata_only(self):
        report = analyze_entries(fixture_entries(), product_code="T-9526G",
                                 volume_id="VANDAL_HEARTS")
        self.assertEqual(report["inventory"]["map_file_count"], 74)
        self.assertEqual(report["inventory"]["map_family_counts"],
                         {"M_IVE": 22, "M_KEY": 17, "M_MAP": 34, "M_SHOW": 1})
        self.assertEqual(report["inventory"]["map_size_bytes_counts"], {"170624": 74})
        self.assertNotIn("payload", str(report))
        self.assertNotIn("must-not-export", str(report))

    def test_missing_pair_member_is_reported_not_guessed(self):
        entries = [e for e in fixture_entries() if e["name"] != "MAP_1_1P.BIN"]
        report = analyze_entries(entries)
        group = next(g for g in report["candidate_groups"]
                     if g["group"] == "numbered_scene_assets_1_1")
        self.assertEqual(group["missing_names"], ["MAP_1_1P.BIN"])
        self.assertIsNone(group["extents_contiguous_in_iso"])
        self.assertFalse(group["runtime_relationship_verified"])

    def test_duplicate_names_case_insensitively_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            analyze_entries([{"name": "A.BIN", "lba": 1, "bytes": 2},
                             {"name": "a.bin", "lba": 2, "bytes": 2}])

    def test_bad_extents_rejected(self):
        for entry in [
            {"name": "A.BIN", "lba": -1, "bytes": 2},
            {"name": "A.BIN", "lba": 1, "bytes": 0},
            {"name": "../A.BIN", "lba": 1, "bytes": 2},
            {"name": "A.BIN", "lba": True, "bytes": 2},
        ]:
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                analyze_entries([entry])

    def test_unknown_map_family_kept_separate(self):
        report = analyze_entries([{"name": "CUSTOM.MAP", "lba": 5, "bytes": 99}])
        self.assertEqual(report["inventory"]["map_family_counts"], {"OTHER_MAP": 1})
        self.assertEqual(report["inventory"]["map_size_bytes_counts"], {"99": 1})

    def test_iso_identity_is_not_translation_authentication(self):
        report = analyze_entries(fixture_entries(), product_code="T-9526G",
                                 volume_id="VANDAL_HEARTS")
        self.assertEqual(report["source"]["product_code"], "T-9526G")
        self.assertFalse(report["source"]["version_authenticated_by_iso_metadata"])
        self.assertIn("Japanese-master equivalence is unverified", " ".join(report["limitations"]))


if __name__ == "__main__":
    unittest.main()
