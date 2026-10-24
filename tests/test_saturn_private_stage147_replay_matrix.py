"""ROM-free synthetic checks of the Stage147 four-control replay classifier."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from tools import saturn_private_same_session_cross_build_prefix as prefix
from tools.saturn_private_stage147_replay_matrix import (
    PAD_RECEIPTS, FRAME_LIMITS, audit_private_stage147_replay_matrix,
)


def png(color, level=6):
    image = Image.new("RGB", (64, 64), color)
    output = BytesIO()
    image.save(output, format="PNG", compress_level=level)
    return output.getvalue()


def private_file(path, data):
    path.write_bytes(data)
    path.chmod(0o600)


def make_capture(path, i, *, base=(20, 30, 40), different_frames=(),
                 sh2_mutation=False, compression=6):
    path.mkdir(mode=0o700)
    common = png(base, compression)
    changed = png((90, 100, 110))
    for frame in prefix.CHECKPOINTS:
        private_file(path / f"frame-{frame}.png",
                     changed if frame in different_frames else common)
    events, state = PAD_RECEIPTS[i]
    private_file(path / "pad-events.txt", events)
    private_file(path / "pad-state.txt", state)
    private_file(path / "frames.stats", (
        f"STAGE99_FRAMES {FRAME_LIMITS[i]}\n"
        "STAGE99_PC_BEFORE 0\nSTAGE99_PC_AFTER 0\n"
        "STAGE99_WIDTH 64\nSTAGE99_HEIGHT 64\n"
    ).encode("ascii"))
    sh2 = "".join(
        f"VH_SH2 frame={n} pc={2 if sh2_mutation and n == 120 else 1}\n"
        for n in prefix.DIAGNOSTIC_FRAMES
    )
    video = "".join(f"VH_VIDEO frame={n} pc=1\n" for n in prefix.DIAGNOSTIC_FRAMES)
    private_file(path / "sh2-window.txt", sh2.encode("ascii"))
    private_file(path / "video-state.txt", video.encode("ascii"))
    private_file(path / "fad.vhcdlog", b"VHCD_FAD 150\nVHCD_FAD 151\n")


def fixture(root, overrides=None):
    overrides = overrides or {}
    paths = tuple(root / f"test-{i}" for i in range(4))
    for i, path in enumerate(paths):
        make_capture(path, i, **overrides.get(i, {}))
    return paths


class Stage147ReplayMatrixTests(unittest.TestCase):
    def test_equal_decoded_pixels_with_recompression(self):
        with tempfile.TemporaryDirectory() as td:
            paths = fixture(Path(td), {1: {"compression": 9}, 3: {"compression": 1}})
            result = audit_private_stage147_replay_matrix(paths)
            self.assertEqual(result["classification"],
                             "decoded_prefix_and_within_build_diagnostics_aligned")
            self.assertEqual(result["checkpoint_count"], 800)
            self.assertTrue(result["within_build_pixels_equal"])
            self.assertTrue(result["within_build_diagnostics_and_fad_equal"])
            self.assertFalse(result["same_host_and_disc_provenance_independently_verified"])
            self.assertFalse(result["runner_sha256_independently_verified_by_this_tool"])
            self.assertFalse(result["source_level_causality_established"])
            self.assertFalse(result["original_media_or_frame_hashes_exported"])

    def test_stable_between_build_difference_without_causal_claim(self):
        with tempfile.TemporaryDirectory() as td:
            paths = fixture(Path(td), {2: {"base": (90, 100, 110)},
                                           3: {"base": (90, 100, 110)}})
            result = audit_private_stage147_replay_matrix(paths)
            self.assertEqual(result["classification"],
                             "repeatable_cross_build_pixel_difference_candidate")
            self.assertEqual(result["comparisons"]["stage144_a__stage144_b"]["pixel_mismatch_count"], 0)
            self.assertEqual(result["comparisons"]["stage145_a__stage145_b"]["pixel_mismatch_count"], 0)
            self.assertEqual(result["comparisons"]["stage144_a__stage145_a"]["pixel_mismatch_count"], 800)
            self.assertTrue(result["cross_build_mismatch_patterns_equal"])
            self.assertFalse(result["battle_or_tactical_player_control_verified"])

    def test_within_stage144_drift_is_not_attributed_to_build_change(self):
        with tempfile.TemporaryDirectory() as td:
            paths = fixture(Path(td), {1: {"different_frames": {7800}}})
            result = audit_private_stage147_replay_matrix(paths)
            self.assertEqual(result["classification"],
                             "within_build_replay_consistency_not_established")
            self.assertEqual(result["comparisons"]["stage144_a__stage144_b"]["pixel_mismatch_count"], 1)
            self.assertEqual(result["comparisons"]["stage144_a__stage144_b"]["first_pixel_mismatch_frame"], 7800)
            self.assertFalse(result["within_build_pixels_equal"])

    def test_diagnostic_drift_prevents_consistency_claim(self):
        with tempfile.TemporaryDirectory() as td:
            paths = fixture(Path(td), {1: {"sh2_mutation": True}})
            result = audit_private_stage147_replay_matrix(paths)
            self.assertTrue(result["within_build_pixels_equal"])
            self.assertFalse(result["within_build_diagnostics_and_fad_equal"])
            self.assertEqual(result["classification"],
                             "within_build_replay_consistency_not_established")

    def test_modified_pad_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            paths = fixture(Path(td))
            private_file(paths[2] / "pad-events.txt", b"VH_PAD mode=1 completed_frames=144000\n")
            with self.assertRaisesRegex(ValueError, "PAD event sequence"):
                audit_private_stage147_replay_matrix(paths)

    def test_incorrect_stage_frame_count_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            paths = fixture(Path(td))
            private_file(paths[3] / "frames.stats",
                         b"STAGE99_FRAMES 132000\nSTAGE99_PC_BEFORE 0\nSTAGE99_PC_AFTER 0\n"
                         b"STAGE99_WIDTH 64\nSTAGE99_HEIGHT 64\n")
            with self.assertRaisesRegex(ValueError, "expected full-stage frame statistics"):
                audit_private_stage147_replay_matrix(paths)

    def test_duplicate_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            paths = fixture(Path(td))
            with self.assertRaisesRegex(ValueError, "must be distinct"):
                audit_private_stage147_replay_matrix((paths[0], paths[1], paths[2], paths[2]))


if __name__ == "__main__":
    unittest.main()
