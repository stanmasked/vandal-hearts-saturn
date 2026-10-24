"""ROM-free Stage149 host-serial orchestration and fail-closed contract tests."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib
import json
import tempfile
import unittest

from tools import saturn_private_stage149_private_replay_coordinator as stage149


def _make_args(td: Path) -> SimpleNamespace:
    private = td / "private"
    private.mkdir(mode=0o700)
    out = td / "captures"
    out.mkdir(mode=0o700)
    kwargs = {}
    for key in stage149.SOURCE_KEYS:
        path = private / key
        content = key.encode("ascii")
        path.write_bytes(content)
        path.chmod(0o600)
        kwargs[key] = path
    kwargs["stage144_runner_sha256"] = hashlib.sha256(b"stage144_executable").hexdigest()
    kwargs["stage145_runner_sha256"] = hashlib.sha256(b"stage145_executable").hexdigest()
    kwargs["output_root"] = out
    kwargs["seconds"] = 5
    return SimpleNamespace(**kwargs)


def _synthetic_audit(stage: int) -> dict:
    """Invented source-free receipt values matching the canonical audit shape."""
    common = {
        "schema_version": 1, "frames_per_process": 132000 if stage == 144 else 144000,
        "paired_cold_boot_processes": 2,
        "checkpoint_png_count_per_process": 1100 if stage == 144 else 1200,
        "all_checkpoint_pngs_and_diagnostic_sequences_verified": True,
        "same_dimensions_across_runs": True,
        "shared_tenth_C_press_frame": 108000, "shared_tenth_C_release_frame": 108006,
        "control_cd_event_count": 10, "intervention_cd_event_count": 10,
        "cd_logs_differ": False, "first_battle_or_player_control_verified": False,
        "requires_private_visual_review_of_dialogue_and_battle_state": True,
        "original_media_or_frame_hashes_exported": False,
    }
    if stage == 144:
        common.update({
            "kind": "STAGE144_PRIVATE_PROLOGUE_CONTINUE_ELEVENTH_C_INTEGRITY_ONLY",
            "eleventh_C_press_frame": 120000, "eleventh_C_release_frame": 120006,
            "pre_eleventh_checkpoint_equal_count": 999,
            "pre_eleventh_checkpoint_total": 999,
            "first_post_eleventh_framebuffer_divergence_by_121200": 120120,
            "first_post_eleventh_framebuffer_divergence_through_132000": 120120,
            "frame_132000_differs": True,
        })
    else:
        common.update({
            "kind": "STAGE145_PRIVATE_PROLOGUE_CONTINUE_TWELFTH_C_INTEGRITY_ONLY",
            "shared_eleventh_C_press_frame": 120000,
            "shared_eleventh_C_release_frame": 120006,
            "twelfth_C_press_frame": 132000, "twelfth_C_release_frame": 132006,
            "twelfth_press_checkpoint_equal": True,
            "pre_twelfth_checkpoint_equal_count": 1099,
            "pre_twelfth_checkpoint_total": 1099,
            "first_post_twelfth_framebuffer_divergence_by_133200": 132120,
            "first_post_twelfth_framebuffer_divergence_through_144000": 132120,
            "frame_144000_differs": True,
        })
    return common


def _runner(stage: int, seen: list, mutation=None, invalid_report=False):
    def invoke(*pos, **kw):
        control, enabled, report = pos[5:8]
        assert kw["seconds"] == 5
        assert control.is_dir() and enabled.is_dir()
        assert not any(control.iterdir()) and not any(enabled.iterdir())
        seen.append(stage)
        obj = {
            "schema": f"vh-saturn-stage{stage}-private-pair-run-1",
            "stage": stage, "run_exit_status": 0,
            "both_private_processes_returned_zero_status": True,
            "runner_sha256_matches_pinned_release": True,
            "original_media_unchanged_before_after": True,
            "runner_unchanged_before_after": True,
            "original_media_or_frame_hashes_exported": False,
            "full_playable_battle_or_unit_control_verified": False,
            "paired_capture_audit": _synthetic_audit(stage),
        }
        if stage == 144:
            obj.update(stage124_drive_readback_receipt_verified=True,
                       stage143_drive_readback_receipt_verified=True,
                       stage124_archive_integrity_gate={"synthetic": True},
                       stage143_owner_only_drive_readback_gate={
                           "stage143_owner_only_drive_readback_verified": True})
        else:
            obj.update(stage144_drive_readback_receipt_verified=True,
                       stage144_owner_only_drive_readback_gate={
                           "stage144_owner_only_drive_readback_verified": True})
        if invalid_report:
            obj["runner_sha256_matches_pinned_release"] = False
        report.write_text(json.dumps(obj) + "\n", encoding="utf8")
        report.chmod(0o600)
        if mutation is not None:
            mutation()
        return {"stage": stage, "run_exit_status": 0, "report_written": True}
    return invoke


def _matrix(paths):
    assert len(paths) == 4
    assert all(p.name.endswith("_control") for p in paths)
    assert [p.name for p in paths] == [
        "stage144_a_control", "stage144_b_control",
        "stage145_a_control", "stage145_b_control",
    ]
    from tools.saturn_private_stage151_evidence_contract import COMPARISON_KEYS
    pairs = {
        key: {
            "pixel_mismatch_count": 0,
            "first_pixel_mismatch_frame": None,
            "pixel_mismatch_ranges": [],
            "sh2_record_mismatch_count": 0,
            "video_record_mismatch_count": 0,
            "fad_common_prefix_record_count": 2,
            "fad_equal": True,
        } for key in COMPARISON_KEYS
    }
    return {
        "schema": "vh-saturn-stage147-four-control-replay-matrix-1",
        "kind": "STAGE147_PRIVATE_CONTROL_REPLAY_MATRIX",
        "labels": ["stage144_a", "stage144_b", "stage145_a", "stage145_b"],
        "checkpoint_count": 800, "frame_start": 120,
        "frame_end": 96000, "frame_step": 120,
        "comparisons": pairs,
        "within_build_pixels_equal": True,
        "within_build_diagnostics_and_fad_equal": True,
        "cross_build_mismatch_patterns_equal": True,
        "classification": "decoded_prefix_and_within_build_diagnostics_aligned",
        "runner_sha256_independently_verified_by_this_tool": False,
        "same_host_and_disc_provenance_independently_verified": False,
        "caller_must_verify_full_paired_capture_audits_and_same_host_media": True,
        "source_level_causality_established": False,
        "original_media_or_frame_hashes_exported": False,
        "private_pixel_hashes_exported": False,
        "battle_or_tactical_player_control_verified": False,
    }


class Stage149CoordinatorTests(unittest.TestCase):
    def setUp(self):
        # ROM-free CI deliberately uses transient runner storage; never allow
        # the real original-disc host guard to run within these mocks.
        guard = patch.object(stage149, "assert_durable_private_workspace",
                             return_value={"capture_and_source_volumes_accepted": True})
        guard.start()
        self.addCleanup(guard.stop)

    def test_interleaved_four_pairs_only_finish_after_all_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            args = _make_args(Path(directory))
            seen = []
            with patch.object(stage149, "_check_media", return_value={}):
                result = stage149.run_private_stage149(
                    args, run144=_runner(144, seen), run145=_runner(145, seen),
                    matrix=_matrix)
            self.assertEqual(seen, [144, 145, 144, 145])
            self.assertTrue(result["experiment_completed"])
            summary_file = args.output_root / "reports" / "stage149-summary.json"
            self.assertEqual(summary_file.stat().st_mode & 0o777, 0o600)
            summary = json.loads(summary_file.read_text())
            self.assertEqual(summary["total_separate_yabause_cold_boots"], 8)
            self.assertFalse(summary["owner_only_drive_upload_and_independent_readback_verified"])
            self.assertFalse(summary["fresh_gameplay_battle_control_verified"])
            self.assertNotIn("cue", json.dumps(summary))
            self.assertNotIn(args.stage144_runner_sha256, json.dumps(summary))
            self.assertEqual(result["classification"],
                             "decoded_prefix_and_within_build_diagnostics_aligned")

    def test_source_mutation_between_pairs_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            args = _make_args(Path(directory))
            seen = []
            def mutate():
                args.track1.write_bytes(b"modified-source")
            with patch.object(stage149, "_check_media", return_value={}):
                with self.assertRaisesRegex(ValueError, "changed between paired runs"):
                    stage149.run_private_stage149(
                        args, run144=_runner(144, seen, mutation=mutate),
                        run145=_runner(145, seen), matrix=_matrix)
            self.assertEqual(seen, [144])
            self.assertFalse((args.output_root / "reports" / "stage149-summary.json").exists())

    def test_invalid_owner_only_pair_report_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            args = _make_args(Path(directory))
            seen = []
            with patch.object(stage149, "_check_media", return_value={}):
                with self.assertRaisesRegex(ValueError, "integrity contract"):
                    stage149.run_private_stage149(
                        args, run144=_runner(144, seen, invalid_report=True),
                        run145=_runner(145, seen), matrix=_matrix)
            self.assertEqual(seen, [144])
            self.assertFalse((args.output_root / "reports" / "stage149-summary.json").exists())

    def test_nonempty_output_root_is_rejected_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            args = _make_args(Path(directory))
            (args.output_root / "resume.txt").write_text("do not resume")
            with self.assertRaisesRegex(ValueError, "completely empty"):
                stage149.run_private_stage149(args)

    def test_runner_digest_wrong_rejected_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            args = _make_args(Path(directory))
            args.stage145_runner_sha256 = "0" * 64
            with self.assertRaisesRegex(ValueError, "pinned release"):
                stage149.run_private_stage149(args)

    def test_corrupted_matrix_does_not_commit_success(self):
        with tempfile.TemporaryDirectory() as directory:
            args = _make_args(Path(directory))
            seen = []
            def corrupt(_):
                bad = _matrix([Path("stage144_a_control"), Path("stage144_b_control"),
                               Path("stage145_a_control"), Path("stage145_b_control")])
                bad["original_media_or_frame_hashes_exported"] = True
                return bad
            with patch.object(stage149, "_check_media", return_value={}):
                with self.assertRaisesRegex(ValueError, "privacy contract"):
                    stage149.run_private_stage149(
                        args, run144=_runner(144, seen), run145=_runner(145, seen),
                        matrix=corrupt)
            self.assertEqual(seen, [144, 145, 144, 145])
            self.assertFalse((args.output_root / "reports" / "stage149-summary.json").exists())


if __name__ == "__main__":
    unittest.main()
