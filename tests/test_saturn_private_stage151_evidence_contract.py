"""ROM-free regressions rejecting incomplete Stage144/145/147 evidence."""
from copy import deepcopy
from pathlib import Path
import unittest

from tools.saturn_private_stage151_evidence_contract import (
    validate_private_pair_report, validate_private_replay_matrix,
)
from test_saturn_private_stage149_private_replay_coordinator import (
    _matrix, _synthetic_audit,
)


def pair_report(stage):
    obj = {
        "schema": f"vh-saturn-stage{stage}-private-pair-run-1",
        "stage": stage, "run_exit_status": 0,
        "both_private_processes_returned_zero_status": True,
        "original_media_unchanged_before_after": True,
        "runner_unchanged_before_after": True,
        "runner_sha256_matches_pinned_release": True,
        "original_media_or_frame_hashes_exported": False,
        "full_playable_battle_or_unit_control_verified": False,
        "paired_capture_audit": _synthetic_audit(stage),
    }
    if stage == 144:
        obj.update({
            "stage124_drive_readback_receipt_verified": True,
            "stage143_drive_readback_receipt_verified": True,
            "stage124_archive_integrity_gate": {"synthetic": True},
            "stage143_owner_only_drive_readback_gate": {
                "stage143_owner_only_drive_readback_verified": True},
        })
    else:
        obj.update({
            "stage144_drive_readback_receipt_verified": True,
            "stage144_owner_only_drive_readback_gate": {
                "stage144_owner_only_drive_readback_verified": True},
        })
    return obj


def matrix_report():
    return _matrix([
        Path("stage144_a_control"), Path("stage144_b_control"),
        Path("stage145_a_control"), Path("stage145_b_control"),
    ])


class Stage151EvidenceContractTests(unittest.TestCase):
    def test_two_full_pair_reports_pass(self):
        for stage in (144, 145):
            with self.subTest(stage=stage):
                validate_private_pair_report(pair_report(stage), stage)

    def test_fake_or_empty_audit_fails(self):
        for stage in (144, 145):
            p = pair_report(stage)
            p["paired_capture_audit"] = {}
            with self.assertRaisesRegex(ValueError, "evidence contract field"):
                validate_private_pair_report(p, stage)

    def test_pre_input_checkpoint_count_must_be_exact(self):
        p = pair_report(145)
        p["paired_capture_audit"]["pre_twelfth_checkpoint_equal_count"] = 1098
        with self.assertRaisesRegex(ValueError, "pre_twelfth_checkpoint_equal_count"):
            validate_private_pair_report(p, 145)

    def test_owner_only_readback_must_be_verified(self):
        p = pair_report(144)
        p["stage143_owner_only_drive_readback_gate"] = {
            "stage143_owner_only_drive_readback_verified": False}
        with self.assertRaisesRegex(ValueError, "owner-only predecessor"):
            validate_private_pair_report(p, 144)

    def test_post_confirm_divergence_must_be_canonical(self):
        p = pair_report(144)
        p["paired_capture_audit"]["first_post_eleventh_framebuffer_divergence_by_121200"] = 120121
        with self.assertRaisesRegex(ValueError, "divergence inconsistent"):
            validate_private_pair_report(p, 144)

    def test_cd_sidecars_required_and_consistent(self):
        p = pair_report(145)
        p["paired_capture_audit"]["intervention_cd_event_count"] = 0
        with self.assertRaisesRegex(ValueError, "CD event count"):
            validate_private_pair_report(p, 145)

    def test_full_matrix_passes(self):
        validate_private_replay_matrix(matrix_report())

    def test_missing_comparison_fails(self):
        p = matrix_report()
        del p["comparisons"]["stage144_b__stage145_b"]
        with self.assertRaisesRegex(ValueError, "exactly six comparisons"):
            validate_private_replay_matrix(p)

    def test_contradictory_mismatch_total_fails(self):
        p = matrix_report()
        p["comparisons"]["stage144_a__stage145_a"]["pixel_mismatch_count"] = 2
        with self.assertRaisesRegex(ValueError, "do not reproduce totals"):
            validate_private_replay_matrix(p)

    def test_forged_classification_fails(self):
        p = matrix_report()
        p["classification"] = "repeatable_cross_build_pixel_difference_candidate"
        with self.assertRaisesRegex(ValueError, "classification"):
            validate_private_replay_matrix(p)

    def test_misleading_evidence_attestation_fails(self):
        p = matrix_report()
        p["same_host_and_disc_provenance_independently_verified"] = True
        with self.assertRaisesRegex(ValueError, "same_host"):
            validate_private_replay_matrix(p)

    def test_forged_report_no_false_true_boolean(self):
        p = pair_report(145)
        p["paired_capture_audit"]["first_battle_or_player_control_verified"] = 0
        with self.assertRaisesRegex(ValueError, "first_battle"):
            validate_private_pair_report(p, 145)


if __name__ == "__main__":
    unittest.main()
