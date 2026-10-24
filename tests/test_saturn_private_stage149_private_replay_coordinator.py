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
            "paired_capture_audit": {"stub": "synthetic-only"},
        }
        if stage == 144:
            obj.update(stage124_drive_readback_receipt_verified=True,
                       stage143_drive_readback_receipt_verified=True,
                       stage143_owner_only_drive_readback_gate={"stub": True})
        else:
            obj.update(stage144_drive_readback_receipt_verified=True,
                       stage144_owner_only_drive_readback_gate={"stub": True})
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
    return {
        "schema": "vh-saturn-stage147-four-control-replay-matrix-1",
        "checkpoint_count": 800,
        "classification": "within_build_replay_consistency_not_established",
        "original_media_or_frame_hashes_exported": False,
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
                             "within_build_replay_consistency_not_established")

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
