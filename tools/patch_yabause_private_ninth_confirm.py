#!/usr/bin/env python3
"""Stage124: add an optional ninth C after the verified Merchant dialogue."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_eighth_confirm import instrument_full_private_eighth_confirm

EIGHTH_SETUP_END = (
    "         vh123_confirm_at8 = (int)n123;\n"
    "         vh123_confirm8_enabled = (vh123_enable8[0] == '1') ? 1 : 0;\n"
)

SETUP_CONFIRM9 = r'''         /* Stage124: both paired runs share the ninth-C frame. */
         const char *vh124_at9 = getenv("VH_SATURN_CONFIRM_AT_FRAME9");
         const char *vh124_enable9 = getenv("VH_SATURN_CONFIRM9_ENABLED");
         int vh124_confirm_at9 = -1;
         int vh124_confirm9_enabled = -1;
         if (vh124_at9 == NULL || vh124_enable9 == NULL ||
             !*vh124_at9 || !*vh124_enable9 ||
             vh123_confirm_at8 < 0 || vh123_confirm8_enabled != 1)
            return 363;
         char *endptr124 = NULL;
         long n124 = strtol(vh124_at9, &endptr124, 10);
         if (endptr124 == vh124_at9 || *endptr124 != '\0' ||
             n124 < (long)vh123_confirm_at8 + 12L ||
             n124 > (long)frames - 8L)
            return 364;
         if (vh124_enable9[1] != '\0' ||
             (vh124_enable9[0] != '0' && vh124_enable9[0] != '1'))
            return 365;
         vh124_confirm_at9 = (int)n124;
         vh124_confirm9_enabled = (vh124_enable9[0] == '1') ? 1 : 0;
'''

CONFIRM9_PRESS = r'''            if (vh124_confirm_at9 >= 0 && frame == vh124_confirm_at9)
            {
               if (vh124_confirm9_enabled)
               {
                  const unsigned char vh124_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh124_mask) == 0U)
                     return 366;
                  PerPadCPressed(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh124_mask) != 0U)
                     return 367;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=PRESS\n",
                      frame, 'C') <= 0)
                     return 368;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=0\n",
                      frame, 'C') <= 0)
                     return 369;
               }
            }
'''

CONFIRM9_RELEASE = r'''            if (vh124_confirm_at9 >= 0 && frame == vh124_confirm_at9 + 6)
            {
               if (vh124_confirm9_enabled)
               {
                  const unsigned char vh124_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh124_mask) != 0U)
                     return 370;
                  PerPadCReleased(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh124_mask) == 0U)
                     return 371;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=RELEASE\n",
                      frame, 'C') <= 0)
                     return 372;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=1\n",
                      frame, 'C') <= 0)
                     return 373;
               }
            }
'''

def instrument_private_ninth_confirm(stage123: bytes) -> bytes:
    source=stage123.decode("utf-8")
    if source.count(MODE_START)!=1 or source.count(MODE_END)!=1:
        raise ValueError("unpinned Stage123 private-frame branch")
    start=source.index(MODE_START)
    end=source.index(MODE_END,start)+len(MODE_END)
    mode=source[start:end]
    if "VH_SATURN_CONFIRM_AT_FRAME9" in mode or "vh124_confirm_at9" in mode:
        raise ValueError("Stage124 ninth confirm already instrumented")
    if mode.count("frames > 96000")!=1 or mode.count("YabauseEmulate()")!=1:
        raise ValueError("Stage124 requires the exact Stage123 96,000-frame cap")
    if mode.count(EIGHTH_SETUP_END)!=1 or mode.count(EMULATE_START)!=1:
        raise ValueError("Stage123 eighth-confirm source anchors differ")
    mode=mode.replace("frames > 96000","frames > 108000",1)
    mode=mode.replace(EIGHTH_SETUP_END,EIGHTH_SETUP_END+SETUP_CONFIRM9,1)
    mode=mode.replace(EMULATE_START,CONFIRM9_PRESS+CONFIRM9_RELEASE+EMULATE_START,1)
    for token,count in (
        ("VH_SATURN_CONFIRM_AT_FRAME9",1),("VH_SATURN_CONFIRM9_ENABLED",1),
        ("vh124_confirm_at9",6),("vh124_confirm9_enabled",4),
        ("PerPadCPressed(vh107_pad);",9),("PerPadCReleased(vh107_pad);",9),
        ("VH_PAD frame=%d button=%c action=PRESS",9),
        ("VH_PAD frame=%d button=%c action=RELEASE",9),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=0",9),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=1",9),
        ("frames > 108000",1),("YabauseEmulate()",1),
    ):
        if mode.count(token)!=count:
            raise ValueError("incomplete Stage124 ninth-confirm instrumentation: "+token)
    if "frames > 96000" in mode:
        raise ValueError("Stage124 retained the old 96,000-frame bound")
    result=source[:start]+mode+source[end:]
    if source.count("vh101_snapshot(")!=result.count("vh101_snapshot("):
        raise ValueError("Stage124 changed inherited video capture")
    if source.count("vh102_snapshot(")!=result.count("vh102_snapshot("):
        raise ValueError("Stage124 changed inherited SH2 capture")
    return result.encode("utf-8")

def instrument_full_private_ninth_confirm(raw: bytes) -> bytes:
    stage123=instrument_full_private_eighth_confirm(raw)
    stage124=instrument_private_ninth_confirm(stage123)
    text=stage124.decode("utf-8")
    for token in (
        "VH_SATURN_START_AT_FRAME","VH_SATURN_CONFIRM_AT_FRAME7",
        "VH_SATURN_CONFIRM7_ENABLED","VH_SATURN_CONFIRM_AT_FRAME8",
        "VH_SATURN_CONFIRM8_ENABLED","VH_SATURN_CONFIRM_AT_FRAME9",
        "VH_SATURN_CONFIRM9_ENABLED","frames > 108000","frames.stats",
        "video-state.txt","sh2-window.txt","pad-state.txt",
    ):
        if token not in text: raise ValueError("incomplete composed Stage124 runner: "+token)
    return stage124

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        if a.source.name!="yui.cpp" or a.output.suffix!=".cpp" or a.output.exists() or a.source.resolve()==a.output.resolve():
            raise ValueError("unsafe pinned source paths")
        with a.output.open("xb") as stream:stream.write(instrument_full_private_ninth_confirm(a.source.read_bytes()))
    except (OSError,ValueError,UnicodeError,TypeError) as exc:
        print("STAGE124_NINTH_CONFIRM_PATCH_REJECTED",type(exc).__name__,str(exc),file=sys.stderr)
        return 1
    print("STAGE124_NINTH_CONFIRM_RUNNER_READY")
    return 0
if __name__=="__main__":sys.exit(main())
