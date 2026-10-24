"""Stage148 source-only, ROM-free spatial and diagnostic comparison tests."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from tools.saturn_private_stage147_replay_matrix import FRAME_LIMITS, PAD_RECEIPTS
from tools.saturn_private_stage148_spatial_drift import (
    _changed_fields, _pixel_regions, audit_private_stage148_spatial_drift,
)
from tools import saturn_private_same_session_cross_build_prefix as prefix


def png(bottom=False, top=False):
    img = Image.new("RGB", (64, 64), (0, 0, 0))
    if top:
        img.paste((0, 0, 3), (0, 0, 64, 19))
    if bottom:
        img.paste((3, 0, 0), (0, 20, 64, 64))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def write_private(path, content):
    path.write_bytes(content)
    path.chmod(0o600)


def capture(root: Path, i: int, *, late_top=False, late_bottom=False, early_diff=False):
    root.mkdir(mode=0o700)
    normal, top, bottom = png(), png(top=True), png(bottom=True)
    for frame in range(120, FRAME_LIMITS[i] + 1, 120):
        if early_diff and frame == 7800:
            data = bottom
        elif i == 2 and 60240 <= frame <= 96000 and late_top:
            data = top
        elif i == 2 and 60240 <= frame <= 96000 and late_bottom:
            data = bottom
        else:
            data = normal
        write_private(root / f"frame-{frame}.png", data)
    write_private(root / "pre.png", normal)
    write_private(root / "post.png", normal)
    ev, state = PAD_RECEIPTS[i]
    write_private(root / "pad-events.txt", ev)
    write_private(root / "pad-state.txt", state)
    write_private(root / "frames.stats", (
        f"STAGE99_FRAMES {FRAME_LIMITS[i]}\nSTAGE99_PC_BEFORE 1\n"
        "STAGE99_PC_AFTER 1\nSTAGE99_WIDTH 64\nSTAGE99_HEIGHT 64\n"
    ).encode("ascii"))
    frames = [0] + list(range(120, FRAME_LIMITS[i] + 1, 120)) + [FRAME_LIMITS[i]]
    sh2 = "".join(
        f"VH_SH2 frame={f} pc=1 r0={3 if i == 2 and late_top and 60240 <= f <= 96000 else 1}\n"
        for f in frames
    )
    video = "".join(f"VH_VIDEO frame={f} pc=1\n" for f in frames)
    write_private(root / "sh2-window.txt", sh2.encode("ascii"))
    write_private(root / "video-state.txt", video.encode("ascii"))
    write_private(root / "fad.vhcdlog", b"VHCD_FAD 150\nVHCD_FAD 151\n")


class Stage148SpatialDriftTests(unittest.TestCase):
    def test_exact_regional_localization_and_r0_correlation(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "capture-a", Path(d) / "capture-b"
            capture(a, 0)
            capture(b, 2, late_top=True)
            result = audit_private_stage148_spatial_drift(a, b)
            phases = result["phases"]
            early = phases["early_120_to_24000"]
            late = phases["late_60120_to_96000"]
            self.assertEqual(result["total_compared_checkpoints"], 800)
            self.assertEqual(early["pixel_differing_checkpoints"], 0)
            self.assertEqual(late["pixel_differing_checkpoints"], 299)
            self.assertEqual(late["top_band_pixel_differences"], 299 * 64 * 19)
            self.assertEqual(late["lower_band_pixel_differences"], 0)
            self.assertTrue(late["top_band_exclusive_when_different"])
            self.assertEqual(late["sh2_changed_fields"], {"r0": 299})
            self.assertEqual(late["sh2_changed_record_count"], 299)
            self.assertEqual(late["video_changed_record_count"], 0)
            self.assertTrue(result["fad_equal"])
            self.assertFalse(result["causal_source_of_drift_established"])
            self.assertFalse(result["original_media_or_frame_hashes_exported"])
            self.assertFalse(result["private_register_values_exported"])

    def test_lower_difference_not_called_top_only(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "capture-a", Path(d) / "capture-b"
            capture(a, 0)
            capture(b, 2, late_bottom=True, early_diff=True)
            result = audit_private_stage148_spatial_drift(a, b)
            early = result["phases"]["early_120_to_24000"]
            late = result["phases"]["late_60120_to_96000"]
            self.assertEqual(early["pixel_differing_checkpoints"], 1)
            self.assertEqual(late["pixel_differing_checkpoints"], 299)
            self.assertFalse(late["top_band_exclusive_when_different"])
            self.assertGreater(late["lower_band_pixel_differences"], 0)

    def test_incomplete_full_capture_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "capture-a", Path(d) / "capture-b"
            capture(a, 0)
            capture(b, 2)
            (b / "frame-143880.png").unlink()
            with self.assertRaisesRegex(ValueError, "full-stage capture file set"):
                audit_private_stage148_spatial_drift(a, b)

    def test_field_validation_and_channel_sensitive_one_pixel_change(self):
        self.assertEqual(
            _changed_fields("VH_SH2 frame=120 pc=1 r0=30", "VH_SH2 frame=120 pc=1 r0=31", "VH_SH2"),
            ("r0",),
        )
        with self.assertRaisesRegex(ValueError, "field key/value"):
            _changed_fields("VH_SH2 frame=120 pc=1 r0=1 r0=2",
                            "VH_SH2 frame=120 pc=1 r0=1", "VH_SH2")
        a = bytes(64 * 64 * 3)
        b = bytearray(a)
        b[0] = 1
        self.assertEqual(_pixel_regions(a, bytes(b), (64, 64)), (1, 0))


if __name__ == "__main__":
    unittest.main()
