#!/usr/bin/env python3
"""Stage107: controlled original Saturn pad START pulse after verified title.

Exact pinned public Yabause Stage106 source only; real media/frames remain
private. Both A/B runs connect the SAME pad. Optional env var provides
a one-shot START pulse, and a numeric private receipt marks when the
button was presented to the emulator (not proof the game accepted it).
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from tools.patch_yabause_original_title_12000 import instrument_original_title_12000

BEFORE = "frames < 1 || frames > 12000 ||"
AFTER = "frames < 1 || frames > 13200 ||"
HEADER = '#include "../vdp2.h"\n'
DECLARE = '         int progress = 0;'
AFTER_INIT = '''         if (!MSH2)
         {
            YabauseDeInit();
            return 204;
         }'''
BEFORE_EMULATE = '''         for (int frame = 0; frame < frames; ++frame)
         {
            if (YabauseEmulate() != 0)'''
BEFORE_RETURN = '''         YabauseDeInit();
         puts("STAGE99_REAL_YABAUSE_BOUND_FRAMES_PASS");'''

SETUP = r'''         /* Stage107 opt-in, frame-indexed Saturn START experiment. */
         const char *vh107_at = getenv("VH_SATURN_START_AT_FRAME");
         int vh107_start_at = -1;
         if (vh107_at && *vh107_at)
         {
            char *endptr = NULL;
            long n = strtol(vh107_at, &endptr, 10);
            if (endptr == vh107_at || *endptr != '\0' ||
                n < 12000L || n > (long)frames - 8L)
               return 223;
            vh107_start_at = (int)n;
         }
         char vh107_pad_log_path[1024];
         if (snprintf(vh107_pad_log_path, sizeof(vh107_pad_log_path),
                      "%s/pad-events.txt", private_dir)
             >= (int)sizeof(vh107_pad_log_path))
            return 224;
         FILE *vh107_pad_log = NULL;
'''

CONNECT = r'''         /* Both control and intervention runs register an identical pad. */
         PerPad_struct *vh107_pad = PerPadAdd(&PORTDATA1);
         if (!vh107_pad)
         {
            YabauseDeInit();
            return 225;
         }
         vh107_pad_log = fopen(vh107_pad_log_path, "wx");
         if (!vh107_pad_log)
         {
            YabauseDeInit();
            return 226;
         }
'''

LOOP = r'''         for (int frame = 0; frame < frames; ++frame)
         {
            /* Set guest pad state BEFORE the frame's YabauseEmulate(). */
            if (vh107_start_at >= 0 && frame == vh107_start_at)
            {
               PerPadStartPressed(vh107_pad);
               if (fprintf(vh107_pad_log,
                   "VH_PAD frame=%d button=START action=PRESS\n",
                   frame) <= 0)
                  return 227;
            }
            if (vh107_start_at >= 0 && frame == vh107_start_at + 6)
            {
               PerPadStartReleased(vh107_pad);
               if (fprintf(vh107_pad_log,
                   "VH_PAD frame=%d button=START action=RELEASE\n",
                   frame) <= 0)
                  return 228;
            }
            if (YabauseEmulate() != 0)'''

FINALIZE = r'''         if (vh107_pad_log)
         {
            if (fprintf(vh107_pad_log,
                "VH_PAD mode=%d completed_frames=%d\n",
                vh107_start_at >= 0 ? 1 : 0, progress) <= 0 ||
                fclose(vh107_pad_log) != 0)
               return 229;
         }
'''


def instrument_gamepad_start(raw: bytes) -> bytes:
    source = instrument_original_title_12000(raw).decode("utf-8")
    replacements=[
        (BEFORE,AFTER),
        (HEADER,HEADER+'#include "../peripheral.h"\n'),
        (DECLARE,DECLARE+"\n"+SETUP),
        (AFTER_INIT,AFTER_INIT+"\n"+CONNECT),
        (BEFORE_EMULATE,LOOP),
        (BEFORE_RETURN,FINALIZE+BEFORE_RETURN),
    ]
    if "vh107_pad_log" in source:
        raise ValueError("already patched original mode")
    for old,new in replacements:
        if source.count(old)!=1:
            raise ValueError("pinned Stage106 Yabause source shape changed: "+old[:24])
        source=source.replace(old,new,1)
    for token in (
        "PerPadAdd(&PORTDATA1)", "PerPadStartPressed(vh107_pad)",
        "PerPadStartReleased(vh107_pad)", "VH_SATURN_START_AT_FRAME",
        AFTER,
    ):
        if source.count(token)!=1:
            raise ValueError("Stage107 original controller instrumentation incomplete")
    if source.count("YabauseEmulate()") != 2:
        raise ValueError("Stage107 changed the guest execution path")
    return source.encode("utf-8")


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        if (a.source.name!="yui.cpp" or a.output.suffix!=".cpp" or
                a.output.exists() or a.source.resolve()==a.output.resolve()):
            raise ValueError("unsafe public Yabause paths")
        with a.output.open("xb") as file:file.write(instrument_gamepad_start(a.source.read_bytes()))
    except (ValueError,OSError,UnicodeError,TypeError):
        print("STAGE107_PINNED_GAMEPAD_SOURCE_REJECTED",file=sys.stderr)
        return 1
    print("STAGE107_PUBLIC_PINNED_SATURN_START_PAD_MODE_READY")
    return 0


if __name__=="__main__":
    sys.exit(main())
