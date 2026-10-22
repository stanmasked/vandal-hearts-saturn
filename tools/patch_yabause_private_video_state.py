#!/usr/bin/env python3
"""Stage101: private numeric VDP1/VDP2/Titan diagnostics on pinned real Yabause.

Records register values and nonzero *counts*, never bytes from original
Saturn game/video RAM. Stage99's original-game frame mode is unchanged
except for a protected optional local numeric video-state audit stream.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_private_game_frames import BOOT_CHECK, instrument_boot_runner

HEADER_ANCHOR = '#include <stdio.h>\nextern "C"\n{\n'
MAIN_ANCHOR = "int main(int argc, char *argv[])\n{\n"
STATE_PATH_ANCHOR = '         char pre_path[1024], post_path[1024], stats_path[1024];'
BEFORE_ANCHOR = '         for (int frame = 0; frame < frames; ++frame)'
CHECKPOINT_ANCHOR = '               if (lodepng::encode(checkpoint_path,'
AFTER_ANCHOR = '         free(pixels);\n         if (remove(gate_path) != 0)'
FINAL_ANCHOR = '         YabauseDeInit();\n         puts("STAGE99_REAL_YABAUSE_BOUND_FRAMES_PASS");'

HELPER = r'''/* Stage101: numeric-only original-video diagnostics; no RAM payload export. */
static unsigned vh101_nonzero(const u8 *data, unsigned length)
{
   unsigned n = 0;
   if (!data) return 0;
   for (unsigned i=0; i<length; ++i)
      n += (data[i] != 0);
   return n;
}
static unsigned vh101_rgb_pixels(const pixel_t *data, int width, int height)
{
   unsigned n = 0;
   if (!data || width <= 0 || height <= 0 || width > 704 || height > 512)
      return 0;
   for (int i=0; i<width*height; ++i)
      n += ((((u32)data[i]) & 0x00ffffffU) != 0U);
   return n;
}
static bool vh101_snapshot(FILE *out, int frame, const pixel_t *pixels,
                           int width, int height)
{
   if (!out || !Vdp1Regs || !Vdp2Regs || !Vdp1Ram ||
       !Vdp2Ram || !Vdp2ColorRam || !MSH2)
      return false;
   sh2regs_struct sh2 = {0};
   SH2GetRegisters(MSH2, &sh2);
   return fprintf(out,
      "VH_VIDEO frame=%d pc=%u tvmd=%u bgon=%u ramctl=%u "
      "vdp1_tvmr=%u vdp1_ptmr=%u vdp1_edsr=%u "
      "vdp1_nz=%u vdp2_nz=%u cram_nz=%u rgb_nz=%u "
      "width=%d height=%d\n",
      frame, (unsigned)sh2.PC, (unsigned)Vdp2Regs->TVMD,
      (unsigned)Vdp2Regs->BGON, (unsigned)Vdp2Regs->RAMCTL,
      (unsigned)Vdp1Regs->TVMR, (unsigned)Vdp1Regs->PTMR,
      (unsigned)Vdp1Regs->EDSR,
      vh101_nonzero(Vdp1Ram, 0x80000U),
      vh101_nonzero(Vdp2Ram, 0x80000U),
      vh101_nonzero(Vdp2ColorRam, 0x1000U),
      vh101_rgb_pixels(pixels, width, height),
      width, height) > 0 && fflush(out) == 0;
}
'''

def instrument_video_probe(original: bytes) -> bytes:
    code = instrument_boot_runner(original).decode("utf-8")
    if (code.count(BOOT_CHECK) != 1 or code.count(HEADER_ANCHOR) != 1 or
            code.count(MAIN_ANCHOR) != 1 or
            "vh101_snapshot" in code):
        raise ValueError("pinned Stage99 runner changed unexpectedly")
    code = code.replace(HEADER_ANCHOR,
                        HEADER_ANCHOR + '#include "../vdp2.h"\n', 1)
    code = code.replace(MAIN_ANCHOR, HELPER + "\n" + MAIN_ANCHOR, 1)
    boot = BOOT_CHECK
    changes = [
        (STATE_PATH_ANCHOR,
         STATE_PATH_ANCHOR +
         '\n         char video_state_path[1024];\n'
         '         FILE *video_state = NULL;\n'
         '         if (snprintf(video_state_path, sizeof(video_state_path),\n'
         '                      "%s/video-state.txt", private_dir) >=\n'
         '                      (int)sizeof(video_state_path)) return 215;'),
        (BEFORE_ANCHOR,
         '         video_state = fopen(video_state_path, "wx");\n'
         '         if (!video_state ||\n'
         '             !vh101_snapshot(video_state, 0, pixels, width, height))\n'
         '         {\n'
         '            if (video_state) fclose(video_state);\n'
         '            free(pixels);\n'
         '            YabauseDeInit();\n'
         '            return 216;\n'
         '         }\n'
         + BEFORE_ANCHOR),
        (CHECKPOINT_ANCHOR,
         '               if (!vh101_snapshot(video_state, progress, pixels,\n'
         '                                   cw, ch))\n'
         '               {\n'
         '                  fclose(video_state);\n'
         '                  free(pixels);\n'
         '                  YabauseDeInit();\n'
         '                  return 217;\n'
         '               }\n'
         + CHECKPOINT_ANCHOR),
        (AFTER_ANCHOR,
         '         if (!vh101_snapshot(video_state, progress, pixels,\n'
         '                             width, height) || fclose(video_state) != 0)\n'
         '         {\n'
         '            free(pixels);\n'
         '            YabauseDeInit();\n'
         '            return 218;\n'
         '         }\n'
         + AFTER_ANCHOR),
    ]
    for old, new in changes:
        if boot.count(old) != 1:
            raise ValueError("Stage99 video probe injection anchor changed")
        boot = boot.replace(old, new, 1)
    if boot.count("vh101_snapshot(") != 3 or code.count(FINAL_ANCHOR) != 1:
        raise ValueError("Stage101 numeric-state snapshot coverage incomplete")
    code = code.replace(BOOT_CHECK, boot, 1)
    if code.count("vh101_snapshot(") != 4:
        raise ValueError("Stage101 helper injection incomplete")
    return code.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if (args.source.resolve() == args.output.resolve() or
                args.output.exists() or args.source.name != "yui.cpp" or
                args.output.suffix != ".cpp"):
            raise ValueError("unexpected runner paths")
        output = instrument_video_probe(args.source.read_bytes())
        with args.output.open("xb") as file:
            file.write(output)
    except (OSError, ValueError, UnicodeError, TypeError):
        print("STAGE101_PINNED_VIDEO_PROBE_INJECTION_REJECTED", file=sys.stderr)
        return 1
    print("STAGE101_PINNED_YABAUSE_NUMERIC_VIDEO_PROBE_PREPARED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
