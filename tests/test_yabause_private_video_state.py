"""Stage101: invented-only numeric VDP/Titan stream contracts."""
import tempfile
from pathlib import Path
import unittest

from tools.patch_yabause_private_video_state import (
    HELPER, instrument_video_probe,
)
from tools.saturn_private_video_state_audit import (
    parse_video_state, inspect_private_video_file,
)


def sample(frame, pc=1, tvmd=32768, bgon=1, vdp2=20, rgb=0):
    return (
        f"VH_VIDEO frame={frame} pc={pc} tvmd={tvmd} bgon={bgon} "
        f"ramctl=0 vdp1_tvmr=0 vdp1_ptmr=0 vdp1_edsr=0 "
        f"vdp1_nz=0 vdp2_nz={vdp2} cram_nz=2 rgb_nz={rgb} "
        f"width=320 height=224\n"
    ).encode()


class Stage101NumericVideoDiagnosticsTests(unittest.TestCase):
    def test_genuine_upstream_source_must_be_pinned(self):
        for raw in (b"", b"int main(){}\n", b"tampered upstream source"):
            with self.subTest(source_len=len(raw)), self.assertRaises(ValueError):
                instrument_video_probe(raw)

    def test_instrumentation_only_computes_counts_not_vram_bytes(self):
        for marker in (
            "Vdp2Regs->TVMD", "Vdp2Regs->BGON",
            "Vdp1Regs->TVMR", "Vdp1Regs->PTMR",
            "Vdp1Ram", "Vdp2Ram", "Vdp2ColorRam",
            "vh101_rgb_pixels", "VH_VIDEO frame=%d",
        ):
            self.assertIn(marker, HELPER)
        self.assertNotIn("fwrite(Vdp2Ram", HELPER)
        self.assertNotIn("fwrite(Vdp1Ram", HELPER)

    def test_raw_black_output_does_not_imply_blank_vram(self):
        report = parse_video_state(
            sample(0, pc=1, vdp2=0) +
            sample(120, pc=2, bgon=1, vdp2=50000, rgb=0) +
            sample(120, pc=2, bgon=1, vdp2=50000, rgb=0)
        )
        self.assertEqual(report["numeric_samples"], 2)
        self.assertEqual(report["final_emulated_frame"], 120)
        self.assertTrue(report["final_vdp2_ram_has_nonzero_data"])
        self.assertEqual(report["frames_with_nonblack_titan_pixels"], [])
        self.assertFalse(report["actual_original_game_title_visible_verified"])

    def test_legitimate_nonblack_output_is_not_first_battle(self):
        report=parse_video_state(
            sample(0,pc=1,tvmd=0,bgon=0)+
            sample(120,pc=2,rgb=80)
        )
        self.assertEqual(report["frames_with_nonblack_titan_pixels"], [120])
        self.assertTrue(report["final_tvmd_display_enable_bit"])
        self.assertTrue(report["vdp2_state_changes_observed"])
        self.assertFalse(report["original_first_battle_visible_verified"])

    def test_frame_order_and_conflicting_repeats_fail(self):
        for data in (
            sample(120) + sample(0),
            sample(0) + sample(0),
            sample(0) + sample(121) + sample(120),
            sample(0) + sample(120) + sample(120, pc=123),
            sample(0) + sample(120) + sample(700),
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse_video_state(data)

    def test_overflows_invalid_pixel_geometry_and_nonnumeric_lines_fail(self):
        for data in (
            sample(0) + sample(120).replace(b"rgb_nz=0", b"rgb_nz=999999"),
            sample(0) + sample(120).replace(b"vdp2_nz=20", b"vdp2_nz=999999"),
            sample(0) + sample(120).replace(b"width=320", b"width=0"),
            sample(0) + sample(120).replace(b"pc=1", b"pc=-1"),
            sample(0) + b"secret raw memory bytes\n",
            sample(0) + sample(120).replace(b"frame=120", b"frame=0120"),
            sample(0) + sample(120).replace(b"\n", b"\r\n"),
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse_video_state(data)

    def test_private_0600_file_in_0700_directory_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            root.chmod(0o700)
            trace=root/"video-state.txt"
            trace.write_bytes(sample(0)+sample(120))
            trace.chmod(0o600)
            self.assertEqual(inspect_private_video_file(trace)["final_emulated_frame"],120)
            trace.chmod(0o644)
            with self.assertRaises(ValueError):
                inspect_private_video_file(trace)
            trace.chmod(0o600)
            alias=root/"video-alias"
            alias.symlink_to(trace)
            with self.assertRaises(ValueError):
                inspect_private_video_file(alias)
            root.chmod(0o755)
            with self.assertRaises(ValueError):
                inspect_private_video_file(trace)


if __name__ == "__main__":
    unittest.main()
