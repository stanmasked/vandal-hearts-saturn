#!/usr/bin/env python3
"""Stage112: add a second guarded START pulse to the pinned private Saturn runner.

Stage101 already records numeric VDP/Titan state and Stage102 already records
the SH2 window. This transformer preserves those witnesses and only changes
the input schedule and bounded frame limit. Public CI uses invented media only.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_pad import SETUP

MODE_MAX = re.compile(r"frames > (?:600|12000|13200)\b")
PRESS_START = '            if (vh107_start_at >= 0 && frame == vh107_start_at)\n            {'
RELEASE_START = '            if (vh107_start_at >= 0 && frame == vh107_start_at + 6)\n            {'
EMULATE_START = '            if (YabauseEmulate() != 0)'
MAIN_ANCHOR = "int main(int argc, char *argv[])\n{\n"
HEADER_ANCHOR = '#include <stdio.h>\nextern "C"\n{\n'
PATH_ANCHOR = "         char pre_path[1024], post_path[1024], stats_path[1024];\n"
PRE_CAPTURE_END = (
    "         if (lodepng::encode(pre_path, (unsigned char*)pixels,\n"
    "                             width, height) != 0)\n"
    "         {\n"
    "            free(pixels);\n"
    "            YabauseDeInit();\n"
    "            return 207;\n"
    "         }\n"
)
CHECKPOINT_ENCODE_ANCHOR = "               if (lodepng::encode(checkpoint_path,\n"
POST_CAPTURE_END = (
    "         if (lodepng::encode(post_path, (unsigned char*)pixels,\n"
    "                             width, height) != 0)\n"
    "         {\n"
    "            free(pixels);\n"
    "            YabauseDeInit();\n"
    "            return 210;\n"
    "         }\n"
)
FINAL_FREE_ANCHOR = "         free(pixels);\n         if (remove(gate_path) != 0)"
LOOP_START = "         for (int frame = 0; frame < frames; ++frame)\n         {\n"

VIDEO_OPEN_ANCHOR = '         video_state = fopen(video_state_path, "wx");\n'
VIDEO_CHECKPOINT_ANCHOR = (
    "               if (!vh101_snapshot(video_state, progress, pixels,\n"
    "                                   cw, ch))\n"
)
VIDEO_FINAL_ANCHOR = (
    "         if (!vh101_snapshot(video_state, progress, pixels,\n"
    "                             width, height) || fclose(video_state) != 0)\n"
)
SH2_OPEN_ANCHOR = '         sh2_window = fopen(sh2_path, "wx");\n'
SH2_CHECKPOINT_ANCHOR = "               if (!vh102_snapshot(sh2_window, progress))\n"
SH2_FINAL_ANCHOR = (
    "         if (!vh102_snapshot(sh2_window, progress) ||\n"
    "             fclose(sh2_window) != 0)\n"
)

SETUP_SECOND_PULSE = r'''         /* Stage112: optional second START pulse at a separately configured frame. */
         const char *vh112_at2 = getenv("VH_SATURN_START_AT_FRAME2");
         int vh112_start_at2 = -1;
         if (vh112_at2 && *vh112_at2)
         {
            char *endptr2 = NULL;
            long n2 = strtol(vh112_at2, &endptr2, 10);
            if (vh107_start_at < 0 || endptr2 == vh112_at2 ||
                *endptr2 != '\0' || n2 < (long)vh107_start_at + 12L ||
                n2 > (long)frames - 8L)
               return 239;
            vh112_start_at2 = (int)n2;
         }
'''


def instrument_private_start_sequence(raw: bytes) -> bytes:
    source = raw.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage109 private frame-boot branch")
    if source.count(MAIN_ANCHOR) != 1 or source.count(HEADER_ANCHOR) != 1:
        raise ValueError("pinned public Yabause main/include anchors differ")
    if "vh112_sh2_snapshot" in source:
        raise ValueError("Stage112 input patch already present")

    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]

    # Keep the Stage107 first pulse unchanged; add a separately guarded pulse.
    if "VH_SATURN_START_AT_FRAME2" in mode or "vh112_start_at2" in mode:
        raise ValueError("Stage112 second pulse already instrumented")
    setup_end = "            vh107_start_at = (int)n;\n         }\n"
    if mode.count(SETUP) != 1 or mode.count(setup_end) != 1:
        raise ValueError("Stage107 first-pulse setup differs from pinned source")
    mode = mode.replace(setup_end, setup_end + SETUP_SECOND_PULSE, 1)

    press_pos = mode.find(PRESS_START)
    release_pos = mode.find(RELEASE_START)
    emulate_pos = mode.find(EMULATE_START)
    if (min(press_pos, release_pos, emulate_pos) < 0 or
            not (press_pos < release_pos < emulate_pos) or
            mode.count(PRESS_START) != 1 or mode.count(RELEASE_START) != 1 or
            mode.count(EMULATE_START) != 1):
        raise ValueError("pinned Stage109 input loop anchors differ")
    press_block = mode[press_pos:release_pos]
    release_block = mode[release_pos:emulate_pos]
    if (press_block.count("PerPadStartPressed(vh107_pad);") != 1 or
            release_block.count("PerPadStartReleased(vh107_pad);") != 1 or
            "VH_PAD frame=%d button=START action=PRESS" not in press_block or
            "VH_PAD frame=%d button=START action=RELEASE" not in release_block or
            "VH_PADSTATE frame=%d start_bit=0" not in press_block or
            "VH_PADSTATE frame=%d start_bit=1" not in release_block):
        raise ValueError("native controller and pad-state witnesses missing")

    second_press = press_block.replace("vh107_start_at", "vh112_start_at2")
    second_release = release_block.replace("vh107_start_at", "vh112_start_at2")
    if (second_press.count("vh112_start_at2") != 2 or
            second_release.count("vh112_start_at2") != 2):
        raise ValueError("second-pulse loop did not remain frame-indexed")
    mode = mode[:emulate_pos] + second_press + second_release + mode[emulate_pos:]

    mode, bound_count = MODE_MAX.subn("frames > 24000", mode)
    if bound_count < 1:
        raise ValueError("no recognized Stage109 bounded frame maximum")

    # Stage101/102 already create both diagnostic streams. Verify that all
    # inherited open/checkpoint/final witnesses are present and ordered; do
    # not add a duplicate fopen or duplicate snapshots.
    for anchor, expected_count, label in (
        (PATH_ANCHOR, 1, "frame path declaration"),
        (PRE_CAPTURE_END, 1, "pre-frame capture"),
        (POST_CAPTURE_END, 1, "post-frame capture"),
        (FINAL_FREE_ANCHOR, 1, "final capture close"),
        (LOOP_START, 1, "guest frame loop"),
        (VIDEO_OPEN_ANCHOR, 1, "Stage101 initial video snapshot"),
        (VIDEO_CHECKPOINT_ANCHOR, 1, "Stage101 checkpoint video snapshot"),
        (VIDEO_FINAL_ANCHOR, 1, "Stage101 final video snapshot"),
        (SH2_OPEN_ANCHOR, 1, "Stage102 initial SH2 snapshot"),
        (SH2_CHECKPOINT_ANCHOR, 1, "Stage102 checkpoint SH2 snapshot"),
        (SH2_FINAL_ANCHOR, 1, "Stage102 final SH2 snapshot"),
        (CHECKPOINT_ENCODE_ANCHOR, 1, "checkpoint PNG encoder"),
    ):
        if mode.count(anchor) != expected_count:
            raise ValueError("Stage112 inherited diagnostic anchor differs: " + label)
    if not (
        mode.index(VIDEO_OPEN_ANCHOR) < mode.index(SH2_OPEN_ANCHOR) < mode.index(LOOP_START)
        and mode.index(VIDEO_CHECKPOINT_ANCHOR) < mode.index(SH2_CHECKPOINT_ANCHOR)
        < mode.index(CHECKPOINT_ENCODE_ANCHOR)
        and mode.index(VIDEO_FINAL_ANCHOR) < mode.index(SH2_FINAL_ANCHOR)
        < mode.index(FINAL_FREE_ANCHOR)
    ):
        raise ValueError("Stage101/102 diagnostic witness order differs from pinned runner")

    if (mode.count("VH_SATURN_START_AT_FRAME2") != 1 or
            mode.count("PerPadStartPressed(vh107_pad);") != 2 or
            mode.count("PerPadStartReleased(vh107_pad);") != 2 or
            mode.count("frames > 24000") < bound_count or
            mode.count("YabauseEmulate()") != 1 or
            mode.count("vh101_snapshot(") != 3 or
            mode.count("vh102_snapshot(") != 3 or
            mode.count("video-state.txt") != 1 or
            mode.count("sh2-window.txt") != 1 or
            mode.count('video_state = fopen(video_state_path, "wx");') != 1 or
            mode.count('sh2_window = fopen(sh2_path, "wx");') != 1):
        raise ValueError("incomplete Stage112 dual-pulse or inherited diagnostic instrumentation")
    source = source[:start] + mode + source[end:]
    if source.count("vh101_snapshot(") != 4 or source.count("vh102_snapshot(") != 4:
        raise ValueError("Stage112 did not preserve Stage101/102 diagnostic coverage")
    return source.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if (args.source.name != "yui.cpp" or args.output.suffix != ".cpp" or
                args.output.exists() or args.source.resolve() == args.output.resolve()):
            raise ValueError("unsafe pinned public Yabause source paths")
        with args.output.open("xb") as stream:
            stream.write(instrument_private_start_sequence(args.source.read_bytes()))
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE112_PRIVATE_START_SEQUENCE_PATCH_REJECTED",
              type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print("STAGE112_PUBLIC_YABAUSE_DUAL_START_PATCH_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
