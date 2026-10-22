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
        MODE_START + "\n         if (frames < 1 || frames > 13200 || invalid) return 1;\n" +
        setup + "\n" + connect + "\n" + loop + "\n" +
        FINALIZE_EXTRA + FINALIZE + "\n         YabauseDeInit();\n" + MODE_END
    )
    return b"int fake_pinned_yui_source(void) {\n" + mode.encode() + b"\nreturn 0;\n}\n"


class Stage112DualStartSourceTests(unittest.TestCase):
    def test_adds_two_separate_native_press_release_blocks(self):
        source = instrument_private_start_sequence(_stage109_instrumented_fixture()).decode()
        start = source.index(MODE_START)
        end = source.index(MODE_END, start) + len(MODE_END)
        mode = source[start:end]
        self.assertEqual(mode.count("PerPadStartPressed(vh107_pad);"), 2)
        self.assertEqual(mode.count("PerPadStartReleased(vh107_pad);"), 2)
        self.assertEqual(mode.count("vh112_start_at2"), 2)
        self.assertEqual(mode.count("VH_PADSTATE frame=%d start_bit=0"), 2)
        self.assertEqual(mode.count("VH_PADSTATE frame=%d start_bit=1"), 2)
        self.assertIn('getenv("VH_SATURN_START_AT_FRAME2")', mode)
        self.assertIn("n2 < (long)vh107_start_at + 12L", mode)
        self.assertIn("n2 > (long)frames - 8L", mode)
        self.assertIn("frames > 24000", mode)
        self.assertIn("VH_PAD mode=%d completed_frames=%d", mode)

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

    def test_does_not_add_media_or_frame_export_logic(self):
        source = instrument_private_start_sequence(_stage109_instrumented_fixture()).decode()
        self.assertNotIn("fwrite(", source)
        self.assertNotIn("upload", source.lower())
        self.assertNotIn("original-saturn.bin", source)
        self.assertNotIn("frame pixels to stdout", source)


if __name__ == "__main__":
    unittest.main()
