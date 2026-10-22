#!/usr/bin/env python3
"""Stage102: private SH2 wait-loop instrumentation built on pinned Stage101.

All original SH2 instruction words and registers stay solely in a protected
LOCAL text file. They are never printed to stdout, pushed to public CI or
included in PR descriptions. Public builds test only invented source/inputs.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from tools.patch_yabause_private_video_state import (
    instrument_video_probe, MAIN_ANCHOR,
)

HELPER = r'''/* Stage102: local-only bounded SH2 registers and instruction window. */
static bool vh102_snapshot(FILE *out, int frame)
{
   if (!out || !MSH2 || !MSH2->MappedMemoryReadWord) return false;
   sh2regs_struct r = {0};
   SH2GetRegisters(MSH2, &r);
   if (r.PC < 0x06000010U || r.PC > 0x060FFFF0U)
      return fprintf(out, "VH_SH2 frame=%d pc=%u valid=0\n",
                     frame, (unsigned)r.PC) > 0 && fflush(out) == 0;
   u16 op[9];
   for (int i=0; i<9; ++i)
      op[i]=MSH2->MappedMemoryReadWord(MSH2, r.PC - 8U + (u32)(2*i));
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


def instrument_sh2_window_on_patched_source(patched: bytes) -> bytes:
    """Add Stage102 SH2 logging to a source that already has Stage101 logging."""
    s = patched.decode("utf-8")
    if s.count(MAIN_ANCHOR) != 1 or "vh102_snapshot" in s:
        raise ValueError("Stage101 pinned source does not match expectations")
    s = s.replace(MAIN_ANCHOR, HELPER + "\n" + MAIN_ANCHOR, 1)
    changes = [
      ('         char video_state_path[1024];',
       '         char video_state_path[1024];\n'
       '         char sh2_path[1024];\n'
       '         FILE *sh2_window = NULL;\n'
       '         if (snprintf(sh2_path, sizeof(sh2_path),\n'
       '                      "%s/sh2-window.txt", private_dir) >=\n'
       '                      (int)sizeof(sh2_path)) return 219;'),
      ('         for (int frame = 0; frame < frames; ++frame)',
       '         sh2_window = fopen(sh2_path, "wx");\n'
       '         if (!sh2_window || !vh102_snapshot(sh2_window, 0))\n'
       '         {\n'
       '            if (sh2_window) fclose(sh2_window);\n'
       '            fclose(video_state);\n'
       '            free(pixels);\n'
       '            YabauseDeInit();\n'
       '            return 220;\n'
       '         }\n'
       '         for (int frame = 0; frame < frames; ++frame)'),
      ('               if (lodepng::encode(checkpoint_path,',
       '               if (!vh102_snapshot(sh2_window, progress))\n'
       '               {\n'
       '                  fclose(sh2_window);\n'
       '                  fclose(video_state);\n'
       '                  free(pixels);\n'
       '                  YabauseDeInit();\n'
       '                  return 221;\n'
       '               }\n'
       '               if (lodepng::encode(checkpoint_path,'),
      ('         free(pixels);\n         if (remove(gate_path) != 0)',
       '         if (!vh102_snapshot(sh2_window, progress) ||\n'
       '             fclose(sh2_window) != 0)\n'
       '         {\n'
       '            free(pixels);\n'
       '            YabauseDeInit();\n'
       '            return 222;\n'
       '         }\n'
       '         free(pixels);\n         if (remove(gate_path) != 0)'),
    ]
    for old, new in changes:
        if s.count(old) != 1:
            raise ValueError("Stage101 SH2 instrumentation anchor modified")
        s = s.replace(old, new, 1)
    if s.count("vh102_snapshot(") != 4:
        raise ValueError("SH2 snapshot callback coverage incomplete")
    return s.encode("utf-8")


def instrument_sh2_window(raw: bytes) -> bytes:
    """Build Stage102 from the pinned Stage99 base for its standalone workflow."""
    return instrument_sh2_window_on_patched_source(instrument_video_probe(raw))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    args=ap.parse_args()
    try:
        if (args.source.name!="yui.cpp" or
            args.output.suffix!=".cpp" or
            args.source.resolve()==args.output.resolve() or
            args.output.exists()):
            raise ValueError("unsafe pinned runner paths")
        with args.output.open("xb") as f:
            f.write(instrument_sh2_window(args.source.read_bytes()))
    except (OSError,ValueError,UnicodeError,TypeError):
        print("STAGE102_PINNED_SH2_WINDOW_REJECTED",file=sys.stderr)
        return 1
    print("STAGE102_PINNED_LOCAL_SH2_WINDOW_READY")
    return 0


if __name__=="__main__":
    sys.exit(main())
