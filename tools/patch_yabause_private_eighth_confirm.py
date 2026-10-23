#!/usr/bin/env python3
"""Stage123: add an optional eighth C after the verified Ash dialogue."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_seventh_confirm import instrument_full_private_seventh_confirm

SEVENTH_SETUP_END = (
    "         vh122_confirm_at7 = (int)n122;\n"
    "         vh122_confirm7_enabled = (vh122_enable7[0] == '1') ? 1 : 0;\n"
)

SETUP_CONFIRM8 = r'''         /* Stage123: both paired runs share the eighth-C frame. */
         const char *vh123_at8 = getenv("VH_SATURN_CONFIRM_AT_FRAME8");
         const char *vh123_enable8 = getenv("VH_SATURN_CONFIRM8_ENABLED");
         int vh123_confirm_at8 = -1;
         int vh123_confirm8_enabled = -1;
         if (vh123_at8 == NULL || vh123_enable8 == NULL ||
             !*vh123_at8 || !*vh123_enable8 ||
             vh122_confirm_at7 < 0 || vh122_confirm7_enabled != 1)
            return 343;
         char *endptr123 = NULL;
         long n123 = strtol(vh123_at8, &endptr123, 10);
         if (endptr123 == vh123_at8 || *endptr123 != '\0' ||
             n123 < (long)vh122_confirm_at7 + 12L ||
             n123 > (long)frames - 8L)
            return 344;
         if (vh123_enable8[1] != '\0' ||
             (vh123_enable8[0] != '0' && vh123_enable8[0] != '1'))
            return 345;
         vh123_confirm_at8 = (int)n123;
         vh123_confirm8_enabled = (vh123_enable8[0] == '1') ? 1 : 0;
'''

CONFIRM8_PRESS = r'''            if (vh123_confirm_at8 >= 0 && frame == vh123_confirm_at8)
            {
               if (vh123_confirm8_enabled)
               {
                  const unsigned char vh123_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh123_mask) == 0U)
                     return 346;
                  PerPadCPressed(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh123_mask) != 0U)
                     return 347;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=PRESS\n",
                      frame, 'C') <= 0)
                     return 348;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=0\n",
                      frame, 'C') <= 0)
                     return 349;
               }
            }
'''

CONFIRM8_RELEASE = r'''            if (vh123_confirm_at8 >= 0 && frame == vh123_confirm_at8 + 6)
            {
               if (vh123_confirm8_enabled)
               {
                  const unsigned char vh123_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh123_mask) != 0U)
                     return 350;
                  PerPadCReleased(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh123_mask) == 0U)
                     return 351;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=RELEASE\n",
                      frame, 'C') <= 0)
                     return 352;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=1\n",
                      frame, 'C') <= 0)
                     return 353;
               }
            }
'''

def instrument_private_eighth_confirm(stage122: bytes) -> bytes:
    source=stage122.decode("utf-8")
    if source.count(MODE_START)!=1 or source.count(MODE_END)!=1:
        raise ValueError("unpinned Stage122 private-frame branch")
    start=source.index(MODE_START)
    end=source.index(MODE_END,start)+len(MODE_END)
    mode=source[start:end]
    if "VH_SATURN_CONFIRM_AT_FRAME8" in mode or "vh123_confirm_at8" in mode:
        raise ValueError("Stage123 eighth confirm already instrumented")
    if mode.count("frames > 84000")!=1 or mode.count("YabauseEmulate()")!=1:
        raise ValueError("Stage123 requires the exact Stage122 84,000-frame cap")
    if mode.count(SEVENTH_SETUP_END)!=1 or mode.count(EMULATE_START)!=1:
        raise ValueError("Stage122 seventh-confirm source anchors differ")
    mode=mode.replace("frames > 84000","frames > 96000",1)
    mode=mode.replace(SEVENTH_SETUP_END,SEVENTH_SETUP_END+SETUP_CONFIRM8,1)
    mode=mode.replace(EMULATE_START,CONFIRM8_PRESS+CONFIRM8_RELEASE+EMULATE_START,1)
    for token,count in (
        ("VH_SATURN_CONFIRM_AT_FRAME8",1),("VH_SATURN_CONFIRM8_ENABLED",1),
        ("vh123_confirm_at8",6),("vh123_confirm8_enabled",4),
        ("PerPadCPressed(vh107_pad);",8),("PerPadCReleased(vh107_pad);",8),
        ("VH_PAD frame=%d button=%c action=PRESS",8),
        ("VH_PAD frame=%d button=%c action=RELEASE",8),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=0",8),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=1",8),
        ("frames > 96000",1),("YabauseEmulate()",1),
    ):
        if mode.count(token)!=count:
            raise ValueError("incomplete Stage123 eighth-confirm instrumentation: "+token)
    if "frames > 84000" in mode:
        raise ValueError("Stage123 retained the old 84,000-frame bound")
    result=source[:start]+mode+source[end:]
    if source.count("vh101_snapshot(")!=result.count("vh101_snapshot("):
        raise ValueError("Stage123 changed inherited video capture")
    if source.count("vh102_snapshot(")!=result.count("vh102_snapshot("):
        raise ValueError("Stage123 changed inherited SH2 capture")
    return result.encode("utf-8")

def instrument_full_private_eighth_confirm(raw: bytes) -> bytes:
    stage122=instrument_full_private_seventh_confirm(raw)
    stage123=instrument_private_eighth_confirm(stage122)
    text=stage123.decode("utf-8")
    for token in (
        "VH_SATURN_START_AT_FRAME","VH_SATURN_CONFIRM_AT_FRAME6",
        "VH_SATURN_CONFIRM6_ENABLED","VH_SATURN_CONFIRM_AT_FRAME7",
        "VH_SATURN_CONFIRM7_ENABLED","VH_SATURN_CONFIRM_AT_FRAME8",
        "VH_SATURN_CONFIRM8_ENABLED","frames > 96000","frames.stats",
        "video-state.txt","sh2-window.txt","pad-state.txt",
    ):
        if token not in text: raise ValueError("incomplete composed Stage123 runner: "+token)
    return stage123

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        if a.source.name!="yui.cpp" or a.output.suffix!=".cpp" or a.output.exists() or a.source.resolve()==a.output.resolve():
            raise ValueError("unsafe pinned source paths")
        with a.output.open("xb") as stream:stream.write(instrument_full_private_eighth_confirm(a.source.read_bytes()))
    except (OSError,ValueError,UnicodeError,TypeError) as exc:
        print("STAGE123_EIGHTH_CONFIRM_PATCH_REJECTED",type(exc).__name__,str(exc),file=sys.stderr)
        return 1
    print("STAGE123_EIGHTH_CONFIRM_RUNNER_READY")
    return 0
if __name__=="__main__":sys.exit(main())
