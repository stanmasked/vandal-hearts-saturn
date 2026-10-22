#!/usr/bin/env python3
"""Stage112: add two guarded START pulses and private numeric Saturn diagnostics.

The generated public executable is built and tested only with invented media.
The SH2/VDP1/VDP2 diagnostics contain numeric state and counts only; original
disc bytes and framebuffer images remain in the user's protected local folder.
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
CHECKPOINT_RENDER_ANCHOR = (
    "               TitanRender(pixels);\n"
    "               if (lodepng::encode(checkpoint_path,\n"
)
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

HELPERS = r'''/* Stage112: local-only numeric SH2 diagnostics. */
static bool vh112_sh2_snapshot(FILE *out, int frame)
{
   if (!out || !MSH2 || !MSH2->MappedMemoryReadWord) return false;
   sh2regs_struct r = {0};
   SH2GetRegisters(MSH2, &r);
   if (r.PC < 0x06000010U || r.PC > 0x060FFFF0U)
      return fprintf(out, "VH_SH2 frame=%d pc=%u valid=0\n",
                     frame, (unsigned)r.PC) > 0 && fflush(out) == 0;
   u16 op[9];
   for (int i = 0; i < 9; ++i)
      op[i] = MSH2->MappedMemoryReadWord(MSH2, r.PC - 8U + (u32)(2 * i));
   return fprintf(out,
      "VH_SH2 frame=%d pc=%u valid=1 sr=%u pr=%u gbr=%u "
      "r0=%u r1=%u r2=%u r3=%u r4=%u r5=%u r15=%u "
      "m8=%u m6=%u m4=%u m2=%u op0=%u p2=%u p4=%u p6=%u p8=%u\n",
      frame, (unsigned)r.PC, (unsigned)r.SR.all,
      (unsigned)r.PR, (unsigned)r.GBR,
      (unsigned)r.R[0], (unsigned)r.R[1], (unsigned)r.R[2],
      (unsigned)r.R[3], (unsigned)r.R[4], (unsigned)r.R[5],
      (unsigned)r.R[15],
      (unsigned)op[0], (unsigned)op[1], (unsigned)op[2],
      (unsigned)op[3], (unsigned)op[4], (unsigned)op[5],
      (unsigned)op[6], (unsigned)op[7], (unsigned)op[8]) > 0 &&
      fflush(out) == 0;
}
'''

PATH_EXTRA = r'''         char sh2_path[1024];
         FILE *sh2_window = NULL;
         if (!private_dir || !*private_dir ||
             snprintf(sh2_path, sizeof(sh2_path),
                      "%s/sh2-window.txt", private_dir) >=
                      (int)sizeof(sh2_path))
            return 240;
'''
OPEN_SH2_DIAGNOSTICS = r'''         sh2_window = fopen(sh2_path, "wx");
         if (!sh2_window || !vh112_sh2_snapshot(sh2_window, 0))
         {
            if (sh2_window) fclose(sh2_window);
            if (video_state) fclose(video_state);
            free(pixels);
            YabauseDeInit();
            return 241;
         }
'''
CHECKPOINT_DIAGNOSTICS = r'''               if (!vh112_sh2_snapshot(sh2_window, progress))
               {
                  if (video_state) fclose(video_state);
                  if (sh2_window) fclose(sh2_window);
                  free(pixels);
                  YabauseDeInit();
                  return 242;
               }
'''
FINAL_DIAGNOSTICS = r'''         bool vh112_diagnostics_ok =
             vh112_sh2_snapshot(sh2_window, progress);
         int vh112_sh2_close = sh2_window ? fclose(sh2_window) : 1;
         if (!vh112_diagnostics_ok || vh112_sh2_close != 0)
         {
            free(pixels);
            YabauseDeInit();
            return 243;
         }
'''
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
CHECKPOINT_ENCODE_ANCHOR = "               if (lodepng::encode(checkpoint_path,\n"


def instrument_private_start_sequence(raw: bytes) -> bytes:
    source = raw.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage109 private frame-boot branch")
    if source.count(MAIN_ANCHOR) != 1 or source.count(HEADER_ANCHOR) != 1:
        raise ValueError("pinned public Yabause main/include anchors differ")
    if "vh112_video_snapshot" in source or "vh112_sh2_snapshot" in source:
        raise ValueError("Stage112 diagnostics already instrumented")
    if '#include "../vdp2.h"' not in source:
        source = source.replace(
            HEADER_ANCHOR, HEADER_ANCHOR + '#include "../vdp2.h"\n', 1
        )
    source = source.replace(MAIN_ANCHOR, HELPERS + "\n" + MAIN_ANCHOR, 1)

    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]

    # Keep the Stage107 first pulse unchanged; add the optional second one
    # after its strict first-pulse parser has finished.
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
    if second_press.count("vh112_start_at2") != 2 or second_release.count("vh112_start_at2") != 2:
        raise ValueError("second-pulse loop did not remain frame-indexed")
    mode = mode[:emulate_pos] + second_press + second_release + mode[emulate_pos:]

    mode, bound_count = MODE_MAX.subn("frames > 24000", mode)
    if bound_count < 1:
        raise ValueError("no recognized Stage109 bounded frame maximum")

    # Stage101 already records numeric VDP/Titan state. Reuse that stream and
    # add only the missing SH2 window, avoiding duplicate opens of video-state.txt.
    for anchor, expected_count, label in (
        (PATH_ANCHOR, 1, "frame path declaration"),
        (PRE_CAPTURE_END, 1, "pre-frame capture"),
        (POST_CAPTURE_END, 1, "post-frame capture"),
        (FINAL_FREE_ANCHOR, 1, "final diagnostic close"),
        (LOOP_START, 1, "guest frame loop"),
        (VIDEO_OPEN_ANCHOR, 1, "Stage101 initial video snapshot"),
        (VIDEO_CHECKPOINT_ANCHOR, 1, "Stage101 checkpoint video snapshot"),
        (VIDEO_FINAL_ANCHOR, 1, "Stage101 final video snapshot"),
        (CHECKPOINT_ENCODE_ANCHOR, 1, "checkpoint PNG encoder"),
    ):
        if mode.count(anchor) != expected_count:
            raise ValueError("Stage112 diagnostic injection anchor differs: " + label)
    if not (mode.index(VIDEO_OPEN_ANCHOR) < mode.index(LOOP_START) and
            mode.index(VIDEO_CHECKPOINT_ANCHOR) < mode.index(CHECKPOINT_ENCODE_ANCHOR) and
            mode.index(VIDEO_FINAL_ANCHOR) < mode.index(FINAL_FREE_ANCHOR)):
        raise ValueError("Stage101 video witness order differs from the pinned runner")
    mode = mode.replace(PATH_ANCHOR, PATH_ANCHOR + PATH_EXTRA, 1)
    mode = mode.replace(LOOP_START, OPEN_SH2_DIAGNOSTICS + LOOP_START, 1)
    mode = mode.replace(CHECKPOINT_ENCODE_ANCHOR,
                        CHECKPOINT_DIAGNOSTICS + CHECKPOINT_ENCODE_ANCHOR, 1)
    mode = mode.replace(FINAL_FREE_ANCHOR, FINAL_DIAGNOSTICS + FINAL_FREE_ANCHOR, 1)

    if (mode.count("VH_SATURN_START_AT_FRAME2") != 1 or
            mode.count("PerPadStartPressed(vh107_pad);") != 2 or
            mode.count("PerPadStartReleased(vh107_pad);") != 2 or
            mode.count("frames > 24000") < bound_count or
            mode.count("YabauseEmulate()") != 1 or
            mode.count("vh112_sh2_snapshot(") != 3 or
            mode.count("video-state.txt") != 1 or
            mode.count("sh2-window.txt") != 1 or
            mode.count('video_state = fopen(video_state_path, "wx");') != 1):
        raise ValueError("incomplete Stage112 dual-pulse or diagnostic instrumentation")
    source = source[:start] + mode + source[end:]
    if source.count("vh112_sh2_snapshot(") != 4:
        raise ValueError("Stage112 SH2 helper or call coverage incomplete")
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
