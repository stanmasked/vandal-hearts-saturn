#!/usr/bin/env python3
"""Stage117: add one optional, guarded third C pulse to advance the next dialogue."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_long_window import instrument_full_private_long_window
from tools.patch_yabause_private_second_confirm import instrument_private_second_confirm
from tools.patch_yabause_private_start_sequence import EMULATE_START

CONFIRM2_SETUP_END = "         vh116_confirm2_enabled = (vh116_enable2[0] == '1') ? 1 : 0;\n"

SETUP_CONFIRM3 = r'''         /* Stage117: keep the second C enabled; isolate one optional third C pulse. */
         const char *vh117_at3 = getenv("VH_SATURN_CONFIRM_AT_FRAME3");
         const char *vh117_enable3 = getenv("VH_SATURN_CONFIRM3_ENABLED");
         int vh117_confirm_at3 = -1;
         int vh117_confirm3_enabled = -1;
         if (vh117_at3 == NULL || vh117_enable3 == NULL || !*vh117_at3 ||
             vh116_confirm_at2 < 0 || vh116_confirm2_enabled != 1)
            return 261;
         char *endptr117 = NULL;
         long n117 = strtol(vh117_at3, &endptr117, 10);
         if (endptr117 == vh117_at3 || *endptr117 != '\0' ||
             n117 < (long)vh116_confirm_at2 + 12L ||
             n117 > (long)frames - 8L)
            return 262;
         if (vh117_enable3[1] != '\0' ||
             (vh117_enable3[0] != '0' && vh117_enable3[0] != '1'))
            return 263;
         vh117_confirm_at3 = (int)n117;
         vh117_confirm3_enabled = (vh117_enable3[0] == '1') ? 1 : 0;
'''

CONFIRM3_PRESS = r'''            if (vh117_confirm_at3 >= 0 && frame == vh117_confirm_at3)
            {
               if (vh117_confirm3_enabled)
               {
                  const unsigned char vh117_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh117_mask) == 0U)
                     return 264;
                  PerPadCPressed(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh117_mask) != 0U)
                     return 265;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=PRESS\n",
                      frame, 'C') <= 0)
                     return 266;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=0\n",
                      frame, 'C') <= 0)
                     return 267;
               }
            }
'''

CONFIRM3_RELEASE = r'''            if (vh117_confirm_at3 >= 0 && frame == vh117_confirm_at3 + 6)
            {
               if (vh117_confirm3_enabled)
               {
                  const unsigned char vh117_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh117_mask) != 0U)
                     return 268;
                  PerPadCReleased(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh117_mask) == 0U)
                     return 269;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=RELEASE\n",
                      frame, 'C') <= 0)
                     return 270;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=1\n",
                      frame, 'C') <= 0)
                     return 271;
               }
            }
'''


def instrument_private_third_confirm(patched: bytes) -> bytes:
    source = patched.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage116 second-confirm runner branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if "frames > 48000" not in mode:
        raise ValueError("Stage117 requires the Stage115 48,000-frame cap")
    if "VH_SATURN_CONFIRM_AT_FRAME2" not in mode or "VH_SATURN_CONFIRM2_ENABLED" not in mode:
        raise ValueError("Stage117 requires Stage116 second-C instrumentation")
    if "VH_SATURN_CONFIRM_AT_FRAME3" in mode or "vh117_confirm_at3" in mode:
        raise ValueError("Stage117 third confirm pulse already instrumented")
    if mode.count(CONFIRM2_SETUP_END) != 1:
        raise ValueError("Stage116 second-confirm setup anchor differs")
    if mode.count(EMULATE_START) != 1 or mode.count("YabauseEmulate()") != 1:
        raise ValueError("Stage116 guest-frame execution anchor differs")

    mode = mode.replace(CONFIRM2_SETUP_END, CONFIRM2_SETUP_END + SETUP_CONFIRM3, 1)
    mode = mode.replace(EMULATE_START, CONFIRM3_PRESS + CONFIRM3_RELEASE + EMULATE_START, 1)
    required_once = (
        ("VH_SATURN_CONFIRM_AT_FRAME3", 1),
        ("VH_SATURN_CONFIRM3_ENABLED", 1),
        ("vh117_confirm_at3", 6),
        ("vh117_confirm3_enabled", 4),
        ("PerPadCPressed(vh107_pad);", 3),
        ("PerPadCReleased(vh107_pad);", 3),
        ("VH_PAD frame=%d button=%c action=PRESS", 3),
        ("VH_PAD frame=%d button=%c action=RELEASE", 3),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=0", 3),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=1", 3),
        ("frames > 48000", 1),
    )
    for token, count in required_once:
        if mode.count(token) != count:
            raise ValueError("incomplete Stage117 third-confirm instrumentation: " + token)
    if mode.count("vh101_snapshot(") != 4 or mode.count("vh102_snapshot(") != 4:
        raise ValueError("Stage117 changed inherited video/SH2 diagnostics")
    return (source[:start] + mode + source[end:]).encode("utf-8")


def instrument_full_private_third_confirm(raw: bytes) -> bytes:
    stage115 = instrument_full_private_long_window(raw)
    stage116 = instrument_private_second_confirm(stage115)
    stage117 = instrument_private_third_confirm(stage116)
    text = stage117.decode("utf-8")
    for token in (
        "VH_SATURN_START_AT_FRAME",
        "VH_SATURN_CONFIRM_AT_FRAME",
        "VH_SATURN_CONFIRM_AT_FRAME2",
        "VH_SATURN_CONFIRM2_ENABLED",
        "VH_SATURN_CONFIRM_AT_FRAME3",
        "VH_SATURN_CONFIRM3_ENABLED",
        "VH_SATURN_CONFIRM_BUTTON",
        "frames > 48000",
        "frames.stats",
        "video-state.txt",
        "sh2-window.txt",
        "pad-state.txt",
    ):
        if token not in text:
            raise ValueError("incomplete composed Stage117 runner: " + token)
    return stage117


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
            stream.write(instrument_full_private_third_confirm(args.source.read_bytes()))
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE117_THIRD_CONFIRM_PATCH_REJECTED",
              type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print("STAGE117_PUBLIC_PINNED_THIRD_CONFIRM_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
