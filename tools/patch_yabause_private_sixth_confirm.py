#!/usr/bin/env python3
"""Stage121: add optional sixth C after the verified Stage119 fifth-C story step."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_fifth_confirm import instrument_full_private_fifth_confirm
from tools.patch_yabause_private_start_sequence import EMULATE_START

FIFTH_SETUP_END = (
    "         vh119_confirm_at5 = (int)n119;\n"
    "         vh119_confirm5_enabled = (vh119_enable5[0] == '1') ? 1 : 0;\n"
)

SETUP_CONFIRM6 = r'''         /* Stage121: both paired runs use the identical sixth-C schedule. */
         const char *vh121_at6 = getenv("VH_SATURN_CONFIRM_AT_FRAME6");
         const char *vh121_enable6 = getenv("VH_SATURN_CONFIRM6_ENABLED");
         int vh121_confirm_at6 = -1;
         int vh121_confirm6_enabled = -1;
         if (vh121_at6 == NULL || vh121_enable6 == NULL ||
             !*vh121_at6 || !*vh121_enable6 ||
             vh119_confirm_at5 < 0 || vh119_confirm5_enabled != 1)
            return 303;
         char *endptr121 = NULL;
         long n121 = strtol(vh121_at6, &endptr121, 10);
         if (endptr121 == vh121_at6 || *endptr121 != '\0' ||
             n121 < (long)vh119_confirm_at5 + 12L ||
             n121 > (long)frames - 8L)
            return 304;
         if (vh121_enable6[1] != '\0' ||
             (vh121_enable6[0] != '0' && vh121_enable6[0] != '1'))
            return 305;
         vh121_confirm_at6 = (int)n121;
         vh121_confirm6_enabled = (vh121_enable6[0] == '1') ? 1 : 0;
'''

CONFIRM6_PRESS = r'''            if (vh121_confirm_at6 >= 0 && frame == vh121_confirm_at6)
            {
               if (vh121_confirm6_enabled)
               {
                  const unsigned char vh121_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh121_mask) == 0U)
                     return 306;
                  PerPadCPressed(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh121_mask) != 0U)
                     return 307;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=PRESS\n",
                      frame, 'C') <= 0)
                     return 308;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=0\n",
                      frame, 'C') <= 0)
                     return 309;
               }
            }
'''

CONFIRM6_RELEASE = r'''            if (vh121_confirm_at6 >= 0 && frame == vh121_confirm_at6 + 6)
            {
               if (vh121_confirm6_enabled)
               {
                  const unsigned char vh121_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh121_mask) != 0U)
                     return 310;
                  PerPadCReleased(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh121_mask) == 0U)
                     return 311;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=RELEASE\n",
                      frame, 'C') <= 0)
                     return 312;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=1\n",
                      frame, 'C') <= 0)
                     return 313;
               }
            }
'''

def instrument_private_sixth_confirm(stage119: bytes) -> bytes:
    source = stage119.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage119 private-frame branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if "VH_SATURN_CONFIRM_AT_FRAME6" in mode or "vh121_confirm_at6" in mode:
        raise ValueError("Stage121 sixth confirm already instrumented")
    if mode.count("frames > 60000") != 1 or mode.count("YabauseEmulate()") != 1:
        raise ValueError("Stage121 requires the exact Stage119 60,000-frame cap")
    if mode.count(FIFTH_SETUP_END) != 1 or mode.count(EMULATE_START) != 1:
        raise ValueError("Stage119 source injection anchors differ")
    mode = mode.replace("frames > 60000", "frames > 72000", 1)
    mode = mode.replace(FIFTH_SETUP_END, FIFTH_SETUP_END + SETUP_CONFIRM6, 1)
    mode = mode.replace(EMULATE_START, CONFIRM6_PRESS + CONFIRM6_RELEASE + EMULATE_START, 1)
    for token,count in (
        ("VH_SATURN_CONFIRM_AT_FRAME6",1),
        ("VH_SATURN_CONFIRM6_ENABLED",1),
        ("vh121_confirm_at6",6),
        ("vh121_confirm6_enabled",4),
        ("PerPadCPressed(vh107_pad);",6),
        ("PerPadCReleased(vh107_pad);",6),
        ("VH_PAD frame=%d button=%c action=PRESS",6),
        ("VH_PAD frame=%d button=%c action=RELEASE",6),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=0",6),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=1",6),
        ("frames > 72000",1),
        ("YabauseEmulate()",1),
    ):
        if mode.count(token)!=count:
            raise ValueError("incomplete Stage121 sixth-confirm instrumentation: "+token)
    source = source[:start] + mode + source[end:]
    if stage119.count(b"vh101_snapshot(") != source.encode().count(b"vh101_snapshot("):
        raise ValueError("Stage121 changed inherited video capture")
    if stage119.count(b"vh102_snapshot(") != source.encode().count(b"vh102_snapshot("):
        raise ValueError("Stage121 changed inherited SH2 capture")
    return source.encode("utf-8")

def instrument_full_private_sixth_confirm(raw: bytes) -> bytes:
    stage119=instrument_full_private_fifth_confirm(raw)
    stage121=instrument_private_sixth_confirm(stage119)
    text=stage121.decode("utf-8")
    for token in (
        "VH_SATURN_START_AT_FRAME", "VH_SATURN_CONFIRM_AT_FRAME5",
        "VH_SATURN_CONFIRM5_ENABLED", "VH_SATURN_CONFIRM_AT_FRAME6",
        "VH_SATURN_CONFIRM6_ENABLED", "frames > 72000", "frames.stats",
        "video-state.txt", "sh2-window.txt", "pad-state.txt",
    ):
        if token not in text: raise ValueError("incomplete Stage121 composed runner: "+token)
    return stage121

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.source.name!='yui.cpp' or args.output.suffix!='.cpp' or args.output.exists() or args.source.resolve()==args.output.resolve():
            raise ValueError('unsafe pinned source paths')
        with args.output.open('xb') as stream:
            stream.write(instrument_full_private_sixth_confirm(args.source.read_bytes()))
    except (OSError,ValueError,UnicodeError,TypeError) as exc:
        print('STAGE121_SIXTH_CONFIRM_PATCH_REJECTED',type(exc).__name__,str(exc),file=sys.stderr)
        return 1
    print('STAGE121_SIXTH_CONFIRM_RUNNER_READY')
    return 0

if __name__=='__main__':sys.exit(main())
