"""Stage99 regression contracts: pinned original Yabause boot-frame mode is opt-in."""
import unittest
from tools.patch_yabause_private_game_frames import (
    MODE, PASS, BOOT_CHECK, STAGE99_CONDITION, instrument_boot_runner,
)


class OriginalPrivateBootFrameContracts(unittest.TestCase):
    def test_only_exact_pinned_public_runner_is_accepted(self):
        for raw in (b"", b"not-a-runner", b"main(){}\n"*600):
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                instrument_boot_runner(raw)

    def test_bounded_user_chosen_frames_and_absolute_original_cd(self):
        self.assertEqual(MODE, "vh-private-frame-boot")
        self.assertIn('argc == 4 && strcmp(argv[1], "vh-private-frame-boot")', STAGE99_CONDITION)
        self.assertIn("frames > 600", BOOT_CHECK)
        self.assertIn("frames < 1", BOOT_CHECK)
        self.assertIn("source_game.cdpath = argv[2];", BOOT_CHECK)
        self.assertIn("source_game.cdcoretype = CDCORE_ISO;", BOOT_CHECK)
        self.assertIn("source_game.skip_load = 0;", BOOT_CHECK)

    def test_real_sh2_and_emulated_bios_not_fake_program(self):
        self.assertIn("SH2CORE_INTERPRETER", BOOT_CHECK)
        self.assertIn("source_game.biospath = NULL;", BOOT_CHECK)
        self.assertIn("YabauseInit(&source_game)", BOOT_CHECK)
        self.assertIn("YabauseEmulate()", BOOT_CHECK)
        self.assertIn("SH2GetRegisters(MSH2, &before)", BOOT_CHECK)
        self.assertIn("SH2GetRegisters(MSH2, &after)", BOOT_CHECK)
        self.assertNotIn("0x7001", BOOT_CHECK)  # Stage83 fake SH2 opcode
        self.assertIn(PASS, BOOT_CHECK)

    def test_video_evidence_only_local_and_has_no_public_assets(self):
        self.assertIn('getenv("VH_SATURN_PRIVATE_FRAMES_DIR")', BOOT_CHECK)
        self.assertIn('"%s/pre.png"', BOOT_CHECK)
        self.assertIn('"%s/post.png"', BOOT_CHECK)
        self.assertIn('"%s/frames.stats"', BOOT_CHECK)
        self.assertIn("TitanGetResolution(&width, &height)", BOOT_CHECK)
        self.assertIn("TitanRender(pixels)", BOOT_CHECK)
        self.assertIn("lodepng::encode(pre_path", BOOT_CHECK)
        self.assertIn("lodepng::encode(post_path", BOOT_CHECK)
        self.assertIn("progress % 120 == 0", BOOT_CHECK)
        self.assertIn("frame-%03d.png", BOOT_CHECK)
        self.assertNotIn('puts("first battle', BOOT_CHECK.lower())

    def test_manual_gate_and_numeric_log_only(self):
        self.assertIn('getenv("VH_SATURN_CAPTURE_GATE")', BOOT_CHECK)
        self.assertIn('getenv("VH_SATURN_FAD_LOG")', BOOT_CHECK)
        self.assertIn('fputs("1\\n", gate)', BOOT_CHECK)
        self.assertIn("remove(gate_path)", BOOT_CHECK)
        self.assertNotIn("fwrite(sector", BOOT_CHECK)
        self.assertNotIn("fprintf(stats, \"STAGE99_FIRST_BATTLE_VERIFIED", BOOT_CHECK)


if __name__ == "__main__":
    unittest.main()
