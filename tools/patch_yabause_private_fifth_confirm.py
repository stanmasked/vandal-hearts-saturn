#!/usr/bin/env python3
"""Stage119: add guarded fifth C pulse after Stage118's fourth-C sequence."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_fourth_confirm import instrument_full_private_fourth_confirm
from tools.patch_yabause_private_start_sequence import EMULATE_START

FOURTH_SETUP_END = (
    "         vh118_confirm_at4 = (int)n118;\n"
    "         vh118_confirm4_enabled = (vh118_enable4[0] == '1') ? 1 : 0;\n"
)

SETUP_CONFIRM5 = r'''         /* Stage119: both processes parse the same fifth-C schedule. */
         const char *vh119_at5 = getenv("VH_SATURN_CONFIRM_AT_FRAME5");
         const char *vh119_enable5 = getenv("VH_SATURN_CONFIRM5_ENABLED");
         int vh119_confirm_at5 = -1;
         int vh119_confirm5_enabled = -1;
         if (vh119_at5 == NULL || vh119_enable5 == NULL || !*vh119_at5 ||
             vh118_confirm_at4 < 0 || vh118_confirm4_enabled != 1)
            return 283;
         char *endptr119 = NULL;
         long n119 = strtol(vh119_at5, &endptr119, 10);
         if (endptr119 == vh119_at5 || *endptr119 != '\0' ||
             n119 < (long)vh118_confirm_at4 + 12L ||
             n119 > (long)frames - 8L)
            return 284;
         if (vh119_enable5[1] != '\0' ||
             (vh119_enable5[0] != '0' && vh119_enable5[0] != '1'))
            return 285;
         vh119_confirm_at5 = (int)n119;
         vh119_confirm5_enabled = (vh119_enable5[0] == '1') ? 1 : 0;
'''

CONFIRM5_PRESS = r'''            if (vh119_confirm_at5 >= 0 && frame == vh119_confirm_at5)
            {
               if (vh119_confirm5_enabled)
               {
                  const unsigned char vh119_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh119_mask) == 0U)
                     return 286;
                  PerPadCPressed(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh119_mask) != 0U)
                     return 287;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=PRESS\n",
                      frame, 'C') <= 0)
                     return 288;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=0\n",
                      frame, 'C') <= 0)
                     return 289;
               }
            }
'''

CONFIRM5_RELEASE = r'''            if (vh119_confirm_at5 >= 0 && frame == vh119_confirm_at5 + 6)
            {
               if (vh119_confirm5_enabled)
               {
                  const unsigned char vh119_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh119_mask) != 0U)
                     return 290;
                  PerPadCReleased(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh119_mask) == 0U)
                     return 291;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=RELEASE\n",
                      frame, 'C') <= 0)
                     return 292;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=1\n",
                      frame, 'C') <= 0)
                     return 293;
               }
            }
'''


def instrument_private_fifth_confirm(patched: bytes) -> bytes:
    source = patched.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage118 frame-boot branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if "frames > 48000" not in mode:
        raise ValueError("Stage119 requires the inherited 48,000-frame cap")
    if "VH_SATURN_CONFIRM_AT_FRAME5" in mode or "vh119_confirm_at5" in mode:
        raise ValueError("Stage119 fifth C already instrumented")
    if mode.count(FOURTH_SETUP_END) != 1:
        raise ValueError("Stage118 fourth-confirm setup anchor differs")
    if mode.count(EMULATE_START) != 1:
        raise ValueError("Stage118 frame execution anchor differs")
    mode = mode.replace(FOURTH_SETUP_END, FOURTH_SETUP_END + SETUP_CONFIRM5, 1)
    mode = mode.replace(EMULATE_START, CONFIRM5_PRESS + CONFIRM5_RELEASE + EMULATE_START, 1)
    for token, count in (
        ("VH_SATURN_CONFIRM_AT_FRAME5", 1),
        ("VH_SATURN_CONFIRM5_ENABLED", 1),
        ("vh119_confirm_at5", 6),
        ("vh119_confirm5_enabled", 4),
        ("PerPadCPressed(vh107_pad);", 5),
        ("PerPadCReleased(vh107_pad);", 5),
        ("VH_PAD frame=%d button=%c action=PRESS", 5),
        ("VH_PAD frame=%d button=%c action=RELEASE", 5),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=0", 5),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=1", 5),
        ("frames > 48000", 1),
        ("YabauseEmulate()", 1),
    ):
        if mode.count(token) != count:
            raise ValueError("incomplete Stage119 fifth-C instrumentation: " + token)
    source = source[:start] + mode + source[end:]
    if source.count("vh101_snapshot(") != 4 or source.count("vh102_snapshot(") != 4:
        raise ValueError("Stage119 changed inherited frame diagnostics")
    return source.encode("utf-8")


def instrument_full_private_fifth_confirm(raw: bytes) -> bytes:
    stage118 = instrument_full_private_fourth_confirm(raw)
    stage119 = instrument_private_fifth_confirm(stage118)
    text = stage119.decode("utf-8")
    for token in (
        "VH_SATURN_START_AT_FRAME", "VH_SATURN_CONFIRM_AT_FRAME",
        "VH_SATURN_CONFIRM_AT_FRAME2", "VH_SATURN_CONFIRM2_ENABLED",
        "VH_SATURN_CONFIRM_AT_FRAME3", "VH_SATURN_CONFIRM3_ENABLED",
        "VH_SATURN_CONFIRM_AT_FRAME4", "VH_SATURN_CONFIRM4_ENABLED",
        "VH_SATURN_CONFIRM_AT_FRAME5", "VH_SATURN_CONFIRM5_ENABLED",
        "frames > 48000", "frames.stats", "video-state.txt",
        "sh2-window.txt", "pad-state.txt",
    ):
        if token not in text:
            raise ValueError("incomplete Stage119 composed runner: " + token)
    return stage119


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if (args.source.name != "yui.cpp" or args.output.suffix != ".cpp" or
                args.output.exists() or args.source.resolve() == args.output.resolve()):
            raise ValueError("unsafe public Yabause source paths")
        with args.output.open("xb") as stream:
            stream.write(instrument_full_private_fifth_confirm(args.source.read_bytes()))
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE119_FIFTH_CONFIRM_PATCH_REJECTED", type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print("STAGE119_FIFTH_CONFIRM_RUNNER_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
