"""Stage75 provenance preflight: synthetic session declarations only."""
import copy
import unittest

from test_saturn_read_crosswalk import inventory
from test_saturn_read_repetition import repeated_trace
from tools.saturn_capture_provenance import audit_capture_provenance

PINNED = "a" * 64
OTHER = "b" * 64


def capture_sidecar():
    return {
        "schema_version": 1,
        "source": {"image_sha256": PINNED, "release_kind": "translation_patched",
                   "product_code": "T-9526G", "private_disc_path": "/secret"},
        "instrumentation": "emulator_cd_block_hook",
        "runs": [
            {"phase": phase,
             "session_id": "session-" + str(i),
             "capture_id": "capture-" + str(i),
             "image_sha256": PINNED,
             "release_kind": "translation_patched",
             "boot_kind": "cold_boot", "frame_start": 10,
             "frame_end": 120, "private_label": "must-not-leak"}
            for i, phase in enumerate((
                "first_battle_entry", "first_battle_entry",
                "menu_control", "menu_control"))
        ],
    }


def inspect(sidecar=None, trace=None, expected=PINNED):
    return audit_capture_provenance(
        inventory(), trace if trace is not None else repeated_trace(),
        sidecar if sidecar is not None else capture_sidecar(),
        expected_image_sha256=expected)


class CaptureProvenanceTests(unittest.TestCase):
    def test_complete_self_consistent_metadata_is_not_authentication(self):
        result = inspect()
        self.assertTrue(result["metadata_preflight_ready_for_human_review"])
        self.assertEqual(result["counts"]["runs"], 4)
        self.assertEqual(result["counts"]["distinct_declared_session_ids"], 4)
        self.assertFalse(result["independent_capture_sessions_verified"])
        self.assertFalse(result["first_battle_map_identified"])
        self.assertFalse(result["source_media_authenticated"])

    def test_perfectly_equal_reads_are_informational_not_rejected(self):
        result = inspect()
        self.assertEqual(result["counts"]["identical_normalized_read_coverage_pairs"],
                         {"first_battle_entry": 1, "menu_control": 1})
        self.assertTrue(result["identical_sector_reads_may_be_legitimate"])
        self.assertTrue(result["metadata_preflight_ready_for_human_review"])

    def test_session_id_collision_rejected_even_with_new_capture_id(self):
        s = capture_sidecar()
        s["runs"][1]["session_id"] = s["runs"][0]["session_id"]
        with self.assertRaisesRegex(ValueError, "reused capture or session"):
            inspect(s)

    def test_capture_id_collision_rejected_even_with_new_session_id(self):
        s = capture_sidecar()
        s["runs"][1]["capture_id"] = s["runs"][0]["capture_id"]
        with self.assertRaisesRegex(ValueError, "reused capture or session"):
            inspect(s)

    def test_wrong_phase_run_count_and_reordering_rejected(self):
        s = capture_sidecar()
        s["runs"][0]["phase"] = "menu_control"
        with self.assertRaisesRegex(ValueError, "phase"):
            inspect(s)
        s = capture_sidecar()
        s["runs"].pop()
        with self.assertRaisesRegex(ValueError, "run count"):
            inspect(s)

    def test_mixed_image_versions_fail_preflight(self):
        s = capture_sidecar()
        s["runs"][1]["image_sha256"] = OTHER
        result = inspect(s)
        self.assertFalse(result["metadata_preflight_ready_for_human_review"])
        self.assertIn("INCONSISTENT_IMAGE_FINGERPRINTS", result["blockers"])
        self.assertEqual(result["counts"]["mixed_image_fingerprint_runs"], 1)

    def test_pinned_reference_mismatch_stops_manual_readiness(self):
        result = inspect(expected=OTHER)
        self.assertIn("REFERENCE_IMAGE_FINGERPRINT_MISMATCH", result["blockers"])
        self.assertFalse(result["metadata_preflight_ready_for_human_review"])

    def test_missing_external_reference_never_claims_baseline(self):
        result = inspect(expected=None)
        self.assertIn("REFERENCE_IMAGE_FINGERPRINT_NOT_SUPPLIED", result["blockers"])

    def test_savestate_boot_is_not_cold_boot(self):
        s = capture_sidecar()
        s["runs"][0]["boot_kind"] = "savestate"
        result = inspect(s)
        self.assertEqual(result["counts"]["non_cold_boot_runs"], 1)
        self.assertIn("SAVESTATE_RUN_NOT_COLD_BOOT", result["blockers"])

    def test_mixed_release_kind_is_explicit_blocker(self):
        s = capture_sidecar()
        s["runs"][3]["release_kind"] = "unmodified"
        result = inspect(s)
        self.assertFalse(result["metadata_preflight_ready_for_human_review"])
        self.assertIn("MIXED_RELEASE_KINDS", result["blockers"])

    def test_capture_windows_require_ordered_nonboolean_frames(self):
        for start, end in ((100, 50), (10, 10), (True, 100),
                           (5, False), (-1, 3), (0, 10000001)):
            with self.subTest(start=start, end=end):
                s = capture_sidecar()
                s["runs"][0]["frame_start"] = start
                s["runs"][0]["frame_end"] = end
                with self.assertRaises(ValueError):
                    inspect(s)

    def test_hashes_are_lowercase_sha256_and_not_booleans(self):
        for value in ("", "A" * 64, True, 1, None, "a"*63):
            with self.subTest(value=value):
                s = capture_sidecar()
                s["source"]["image_sha256"] = value
                with self.assertRaises(ValueError):
                    inspect(s)

    def test_bad_identifiers_cannot_be_paths_or_containers(self):
        for value in ("/secret/run", "capture:1", "", [], {}, True):
            with self.subTest(value=value):
                s = capture_sidecar()
                s["runs"][0]["capture_id"] = value
                with self.assertRaises(ValueError):
                    inspect(s)

    def test_instrumentation_product_and_schema_are_strict(self):
        for key, value in (("instrumentation", []),
                           ("instrumentation", "unreviewed_tool"),
                           ("schema_version", True)):
            s = capture_sidecar()
            s[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                inspect(s)
        s = capture_sidecar()
        s["source"]["product_code"] = "wrong game"
        with self.assertRaises(ValueError):
            inspect(s)

    def test_insufficient_runs_not_promoted_by_unique_ids(self):
        s = capture_sidecar()
        t = repeated_trace()
        s["runs"] = [s["runs"][0], s["runs"][2]]
        t["runs"] = [t["runs"][0], t["runs"][2]]
        result = inspect(s, t)
        self.assertFalse(result["metadata_preflight_ready_for_human_review"])
        self.assertIn("INSUFFICIENT_REPEATED_SECTOR_RUNS", result["blockers"])

    def test_response_has_no_identifiers_media_hashes_or_private_paths(self):
        s = capture_sidecar()
        s["runs"][0]["private_label"] = "some-very-private-token"
        r = str(inspect(s))
        for private in (PINNED, "capture-0", "session-0", "some-very-private-token",
                        "/secret", "T-9526G", "translation_patched"):
            self.assertNotIn(private, r)


if __name__ == "__main__":
    unittest.main()
