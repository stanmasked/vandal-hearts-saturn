#!/usr/bin/env python3
"""Stage122: add an optional seventh C after the verified Merchant/Ash scene."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_sixth_confirm import (
    CONFIRM6_PRESS, CONFIRM6_RELEASE, instrument_full_private_sixth_confirm,
)

SIXTH_SETUP_END = (
    "         vh121_confirm_at6 = (int)n121;\\n"
    "         vh121_confirm6_enabled = (vh121_enable6[0] == '1') ? 1 : 0;\\n"
)

SETUP_CONFIRM7 = r'''         /* Stage122: both paired runs share the seventh-C frame. */
         const char *vh122_at7 = getenv("VH_SATURN_CONFIRM_AT_FRAME7");
         const char *vh122_enable7 = getenv("VH_SATURN_CONFIRM7_ENABLED");
         int vh122_confirm_at7 = -1;
         int vh122_confirm7_enabled = -1;
         if (vh122_at7 == NULL || vh122_enable7 == NULL ||
             !*vh122_at7 || !*vh122_enable7 ||
             vh121_confirm_at6 < 0 || vh121_confirm6_enabled != 1)
            return 323;
         char *endptr122 = NULL;
         long n122 = strtol(vh122_at7, &endptr122, 10);
         if (endptr122 == vh122_at7 || *endptr122 != '\0' ||
             n122 < (long)vh121_confirm_at6 + 12L ||
             n122 > (long)frames - 8L)
            return 324;
         if (vh122_enable7[1] != '\0' ||
             (vh122_enable7[0] != '0' && vh122_enable7[0] != '1'))
            return 325;
         vh122_confirm_at7 = (int)n122;
         vh122_confirm7_enabled = (vh122_enable7[0] == '1') ? 1 : 0;
'''

CONFIRM7_PRESS = r'''            if (vh122_confirm_at7 >= 0 && frame == vh122_confirm_at7)
            {
               if (vh122_confirm7_enabled)
               {
                  const unsigned char vh122_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh122_mask) == 0U)
                     return 326;
                  PerPadCPressed(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh122_mask) != 0U)
                     return 327;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=PRESS\n",
                      frame, 'C') <= 0)
                     return 328;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=0\n",
                      frame, 'C') <= 0)
                     return 329;
               }
            }
'''

CONFIRM7_RELEASE = r'''            if (vh122_confirm_at7 >= 0 && frame == vh122_confirm_at7 + 6)
            {
               if (vh122_confirm7_enabled)
               {
                  const unsigned char vh122_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh122_mask) != 0U)
                     return 330;
                  PerPadCReleased(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh122_mask) == 0U)
                     return 331;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=RELEASE\n",
                      frame, 'C') <= 0)
                     return 332;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=1\n",
                      frame, 'C') <= 0)
                     return 333;
               }
            }
'''

def instrument_private_seventh_confirm(stage121: bytes) -> bytes:
    source=stage121.decode("utf-8")
    if source.count(MODE_START)!=1 or source.count(MODE_END)!=1:
        raise ValueError("unpinned Stage121 private-frame branch")
    start=source.index(MODE_START)
    end=source.index(MODE_END,start)+len(MODE_END)
    mode=source[start:end]
    if "VH_SATURN_CONFIRM_AT_FRAME7" in mode or "vh122_confirm_at7" in mode:
        raise ValueError("Stage122 seventh confirm already instrumented")
    if mode.count("frames > 72000")!=1 or mode.count("YabauseEmulate()")!=1:
        raise ValueError("Stage122 requires the exact Stage121 72,000-frame cap")
    if mode.count(SIXTH_SETUP_END)!=1 or mode.count(EMULATE_START)!=1:
        raise ValueError("Stage121 sixth-confirm source anchors differ")
    mode=mode.replace("frames > 72000","frames > 84000",1)
    mode=mode.replace(SIXTH_SETUP_END,SIXTH_SETUP_END+SETUP_CONFIRM7,1)
    mode=mode.replace(EMULATE_START,CONFIRM7_PRESS+CONFIRM7_RELEASE+EMULATE_START,1)
    for token,count in (
        ("VH_SATURN_CONFIRM_AT_FRAME7",1),("VH_SATURN_CONFIRM7_ENABLED",1),
        ("vh122_confirm_at7",6),("vh122_confirm7_enabled",4),
        ("PerPadCPressed(vh107_pad);",7),("PerPadCReleased(vh107_pad);",7),
        ("VH_PAD frame=%d button=%c action=PRESS",7),
        ("VH_PAD frame=%d button=%c action=RELEASE",7),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=0",7),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=1",7),
        ("frames > 84000",1),("YabauseEmulate()",1),
    ):
        if mode.count(token)!=count:
            raise ValueError("incomplete Stage122 seventh-confirm instrumentation: "+token)
    if "frames > 72000" in mode:
        raise ValueError("Stage122 retained the old 72,000-frame bound")
    result=source[:start]+mode+source[end:]
    if source.count("vh101_snapshot(")!=result.count("vh101_snapshot("):
        raise ValueError("Stage122 changed inherited video capture")
    if source.count("vh102_snapshot(")!=result.count("vh102_snapshot("):
        raise ValueError("Stage122 changed inherited SH2 capture")
    return result.encode("utf-8")

def instrument_full_private_seventh_confirm(raw: bytes) -> bytes:
    stage121=instrument_full_private_sixth_confirm(raw)
    stage122=instrument_private_seventh_confirm(stage121)
    text=stage122.decode("utf-8")
    for token in (
        "VH_SATURN_START_AT_FRAME","VH_SATURN_CONFIRM_AT_FRAME5",
        "VH_SATURN_CONFIRM5_ENABLED","VH_SATURN_CONFIRM_AT_FRAME6",
        "VH_SATURN_CONFIRM6_ENABLED","VH_SATURN_CONFIRM_AT_FRAME7",
        "VH_SATURN_CONFIRM7_ENABLED","frames > 84000","frames.stats",
        "video-state.txt","sh2-window.txt","pad-state.txt",
    ):
        if token not in text: raise ValueError("incomplete composed Stage122 runner: "+token)
    return stage122

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        if a.source.name!="yui.cpp" or a.output.suffix!=".cpp" or a.output.exists() or a.source.resolve()==a.output.resolve():
            raise ValueError("unsafe pinned source paths")
        with a.output.open("xb") as stream:stream.write(instrument_full_private_seventh_confirm(a.source.read_bytes()))
    except (OSError,ValueError,UnicodeError,TypeError) as exc:
        print("STAGE122_SEVENTH_CONFIRM_PATCH_REJECTED",type(exc).__name__,str(exc),file=sys.stderr)
        return 1
    print("STAGE122_SEVENTH_CONFIRM_RUNNER_READY")
    return 0
if __name__=="__main__":sys.exit(main())
