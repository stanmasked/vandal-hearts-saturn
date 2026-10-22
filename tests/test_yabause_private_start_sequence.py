"""Stage112 source-only tests: dual START pulses, bounded long window, no media."""
import unittest

from tools.patch_yabause_native_start_bit import (
    MODE_START, MODE_END, SETUP_EXTRA, CONNECT_EXTRA, PRESS_EXTRA,
    RELEASE_EXTRA, FINALIZE_EXTRA,
)
from tools.patch_yabause_private_start_pad import (
    SETUP, CONNECT, LOOP, FINALIZE,
)
from tools.patch_yabause_private_start_sequence import instrument_private_start_sequence


def _stage109_instrumented_fixture():
    setup = SETUP + SETUP_EXTRA
    connect = CONNECT + CONNECT_EXTRA
    loop = LOOP.replace(
        "               PerPadStartPressed(vh107_pad);\n",
        "               PerPadStartPressed(vh107_pad);\n" + PRESS_EXTRA,
    ).replace(
        "               PerPadStartReleased(vh107_pad);\n",
        "               PerPadStartReleased(vh107_pad);\n" + RELEASE_EXTRA,
    )
    mode = (
        MODE_START + "\n"
        "         if (frames < 1 || frames > 13200 || invalid) return 1;\n"
        "         char pre_path[1024], post_path[1024], stats_path[1024];\n"
        "         char video_state_path[1024];\n"
        "         FILE *video_state = NULL;\n"
        '         if (snprintf(video_state_path, sizeof(video_state_path),\n'
        '                      "%s/video-state.txt", private_dir) >=\n'
        '                      (int)sizeof(video_state_path)) return 215;\n'
        "         pixel_t *pixels = NULL;\n"
        "         int width = 64, height = 64, progress = 0;\n"
        + setup + "\n" + connect + "\n"
        "         TitanRender(pixels);\n"
        "         if (lodepng::encode(pre_path, (unsigned char*)pixels,\n"
        "                             width, height) != 0)\n"
        "         {\n"
        "            free(pixels);\n"
        "            YabauseDeInit();\n"
        "            return 207;\n"
        "         }\n"
        '         video_state = fopen(video_state_path, "wx");\n'
        "         if (!video_state ||\n"
        "             !vh101_snapshot(video_state, 0, pixels, width, height))\n"
        "         {\n"
        "            if (video_state) fclose(video_state);\n"
        "            free(pixels);\n"
        "            YabauseDeInit();\n"
        "            return 216;\n"
        "         }\n"
        + loop + "\n"
        "            { return 1; }\n"
        "            progress++;\n"
        "            if (progress % 120 == 0)\n"
        "            {\n"
        "               int cw = 64, ch = 64;\n"
        "               char checkpoint_path[1024];\n"
        "               TitanRender(pixels);\n"
        "               if (!vh101_snapshot(video_state, progress, pixels,\n"
        "                                   cw, ch))\n"
        "               {\n"
        "                  fclose(video_state);\n"
        "                  free(pixels);\n"
        "                  YabauseDeInit();\n"
        "                  return 217;\n"
        "               }\n"
        "               if (lodepng::encode(checkpoint_path,\n"
        "                                   (unsigned char*)pixels, cw, ch) != 0)\n"
        "                  return 1;\n"
        "            }\n"
        "         }\n"
        "         TitanRender(pixels);\n"
        "         if (lodepng::encode(post_path, (unsigned char*)pixels,\n"
        "                             width, height) != 0)\n"
        "         {\n"
        "            free(pixels);\n"
        "            YabauseDeInit();\n"
        "            return 210;\n"
        "         }\n"
        "         if (!vh101_snapshot(video_state, progress, pixels,\n"
        "                             width, height) || fclose(video_state) != 0)\n"
        "         {\n"
        "            free(pixels);\n"
        "            YabauseDeInit();\n"
        "            return 218;\n"
        "         }\n"
        "         free(pixels);\n"
        "         if (remove(gate_path) != 0) return 1;\n"
        + FINALIZE_EXTRA + FINALIZE + "\n         YabauseDeInit();\n" + MODE_END
    )
    return (
        '#include <stdio.h>\nextern "C"\n{\n}\n'
        "int main(int argc, char *argv[])\n{\n" +
        mode + "\nreturn 0;\n}\n"
    ).encode()


class Stage112DualStartSourceTests(unittest.TestCase):
    def test_adds_two_separate_native_press_release_blocks(self):
        source = instrument_private_start_sequence(_stage109_instrumented_fixture()).decode()
        start = source.index(MODE_START)
        end = source.index(MODE_END, start) + len(MODE_END)
        mode = source[start:end]
        self.assertEqual(mode.count("PerPadStartPressed(vh107_pad);"), 2)
        self.assertEqual(mode.count("PerPadStartReleased(vh107_pad);"), 2)
        self.assertEqual(mode.count("frame == vh112_start_at2"), 1)
        self.assertEqual(mode.count("frame == vh112_start_at2 + 6"), 1)
        self.assertEqual(mode.count("VH_PADSTATE frame=%d start_bit=0"), 2)
        self.assertEqual(mode.count("VH_PADSTATE frame=%d start_bit=1"), 2)
        self.assertIn('getenv("VH_SATURN_START_AT_FRAME2")', mode)
        self.assertIn("n2 < (long)vh107_start_at + 12L", mode)
        self.assertIn("n2 > (long)frames - 8L", mode)
        self.assertIn("frames > 24000", mode)
        self.assertIn("VH_PAD mode=%d completed_frames=%d", mode)
        self.assertIn("video-state.txt", mode)
        self.assertIn("sh2-window.txt", mode)
        self.assertEqual(mode.count("vh112_sh2_snapshot("), 3)
        self.assertEqual(source.count("vh112_sh2_snapshot("), 4)
        self.assertNotIn("vh112_video_snapshot(", source)
        self.assertEqual(mode.count('video_state = fopen(video_state_path, "wx");'), 1)
        self.assertIn("vh101_snapshot(video_state, progress, pixels", source)
        self.assertIn("VH_SH2 frame=%d pc=%u valid=1", source)

    def test_first_pulse_remains_compatible_and_second_pulse_is_optional(self):
        source = instrument_private_start_sequence(_stage109_instrumented_fixture()).decode()
        self.assertIn('getenv("VH_SATURN_START_AT_FRAME")', source)
        self.assertIn('getenv("VH_SATURN_START_AT_FRAME2")', source)
        self.assertIn("int vh112_start_at2 = -1;", source)
        self.assertIn("frame == vh107_start_at", source)
        self.assertIn("frame == vh112_start_at2", source)
        self.assertIn("frame == vh112_start_at2 + 6", source)

    def test_rejects_tampered_or_incomplete_source(self):
        for raw in (
            b"",
            b"int main(){return 0;}",
            _stage109_instrumented_fixture().replace(
                b"PerPadStartReleased(vh107_pad);", b"PerPadReleaseTampered(vh107_pad);"
            ),
            _stage109_instrumented_fixture().replace(
                b"frames > 13200", b"frames > 17000"
            ),
        ):
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                instrument_private_start_sequence(raw)

    def test_rejects_missing_real_framebuffer_diagnostic_anchor(self):
        raw = _stage109_instrumented_fixture().replace(
            b"if (lodepng::encode(checkpoint_path,",
            b"if (tampered_png_encoder(checkpoint_path,",
        )
        with self.assertRaisesRegex(ValueError, "checkpoint PNG encoder"):
            instrument_private_start_sequence(raw)

    def test_does_not_add_media_or_frame_export_logic(self):
        source = instrument_private_start_sequence(_stage109_instrumented_fixture()).decode()
        self.assertNotIn("fwrite(", source)
        self.assertNotIn("upload", source.lower())
        self.assertNotIn("original-saturn.bin", source)
        self.assertNotIn("frame pixels to stdout", source)


if __name__ == "__main__":
    unittest.main()
