#!/usr/bin/env python3
"""Stage116: add one bounded follow-up C pulse after Stage115's New Game confirm."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_confirm_pad import SETUP_CONFIRM
from tools.patch_yabause_private_long_window import instrument_full_private_long_window
from tools.patch_yabause_private_start_sequence import EMULATE_START

SETUP_FOLLOWUP = r'''         /* Stage116: optional C pulse to advance the opening mission dialogue. */
         const char *vh116_at_env = getenv("VH_SATURN_FOLLOWUP_C_AT_FRAME");
         int vh116_followup_at = -1;
         if (vh116_at_env != NULL)
         {
            if (!*vh116_at_env || vh114_confirm_at < 0 ||
                vh114_confirm_button != 'C' || vh112_start_at2 >= 0)
               return 250;
            char *endptr116 = NULL;
            long n116 = strtol(vh116_at_env, &endptr116, 10);
            if (endptr116 == vh116_at_env || *endptr116 != '\0' ||
                n116 < (long)vh114_confirm_at + 12L ||
                n116 > (long)frames - 8L)
               return 251;
            vh116_followup_at = (int)n116;
         }
'''

FOLLOWUP_PRESS = r'''            if (vh116_followup_at >= 0 && frame == vh116_followup_at)
            {
               const unsigned char vh116_mask = 0x02U;
               if ((vh107_pad->padbits[0] & vh116_mask) != vh116_mask)
                  return 252;
               PerPadCPressed(vh107_pad);
               if ((vh107_pad->padbits[0] & vh116_mask) != 0U)
                  return 253;
               if (fprintf(vh107_pad_log,
                   "VH_PAD frame=%d button=C action=PRESS\n", frame) <= 0)
                  return 254;
               if (fprintf(vh109_state_log,
                   "VH_PADSTATE frame=%d button=C active_low_bit=0\n", frame) <= 0)
                  return 255;
            }
'''

FOLLOWUP_RELEASE = r'''            if (vh116_followup_at >= 0 && frame == vh116_followup_at + 6)
            {
               const unsigned char vh116_mask = 0x02U;
               PerPadCReleased(vh107_pad);
               if ((vh107_pad->padbits[0] & vh116_mask) == 0U)
                  return 256;
               if (fprintf(vh107_pad_log,
                   "VH_PAD frame=%d button=C action=RELEASE\n", frame) <= 0)
                  return 257;
               if (fprintf(vh109_state_log,
                   "VH_PADSTATE frame=%d button=C active_low_bit=1\n", frame) <= 0)
                  return 258;
            }
'''


def instrument_private_followup_c(patched: bytes) -> bytes:
    """Add one C press/release pair without changing the Stage115 frame loop."""
    source = patched.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage115 private frame-boot branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if "VH_SATURN_FOLLOWUP_C_AT_FRAME" in mode or "vh116_followup_at" in mode:
        raise ValueError("Stage116 follow-up C input already instrumented")
    if mode.count(SETUP_CONFIRM) != 1:
        raise ValueError("Stage114 initial A/C setup differs from pinned source")
    if mode.count(EMULATE_START) != 1 or mode.count("YabauseEmulate()") != 1:
        raise ValueError("Stage115 guest-frame loop differs from pinned source")
    if "frames > 48000" not in mode or "frames > 24000" in mode:
        raise ValueError("Stage115 48,000-frame fail-closed bound differs")

    mode = mode.replace(SETUP_CONFIRM, SETUP_CONFIRM + SETUP_FOLLOWUP, 1)
    mode = mode.replace(EMULATE_START, FOLLOWUP_PRESS + FOLLOWUP_RELEASE + EMULATE_START, 1)
    required_once = (
        ("VH_SATURN_FOLLOWUP_C_AT_FRAME", 1),
        ("PerPadCPressed(vh107_pad);", 2),
        ("PerPadCReleased(vh107_pad);", 2),
        ("VH_PAD frame=%d button=C action=PRESS", 1),
        ("VH_PAD frame=%d button=C action=RELEASE", 1),
        ("frames > 48000", 1),
        ("VH_PADSTATE frame=%d button=C active_low_bit=0", 1),
        ("VH_PADSTATE frame=%d button=C active_low_bit=1", 1),
    )
    for token, count in required_once:
        if mode.count(token) != count:
            raise ValueError("incomplete Stage116 follow-up instrumentation: " + token)
    if mode.count("vh101_snapshot(") < 2 or mode.count("vh102_snapshot(") < 2:
        raise ValueError("Stage116 lost inherited video/SH2 diagnostics")
    return (source[:start] + mode + source[end:]).encode("utf-8")


def instrument_full_private_followup_c(raw: bytes) -> bytes:
    stage115 = instrument_full_private_long_window(raw)
    stage116 = instrument_private_followup_c(stage115)
    text = stage116.decode("utf-8")
    required = (
        "VH_SATURN_START_AT_FRAME",
        "VH_SATURN_CONFIRM_AT_FRAME",
        "VH_SATURN_CONFIRM_BUTTON",
        "VH_SATURN_FOLLOWUP_C_AT_FRAME",
        "PerPadCPressed(vh107_pad);",
        "PerPadCReleased(vh107_pad);",
        "frames > 48000",
        "frames.stats",
        "video-state.txt",
        "sh2-window.txt",
        "pad-state.txt",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise ValueError("incomplete composed Stage116 pipeline: " + ", ".join(missing))
    return stage116


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
            stream.write(instrument_full_private_followup_c(args.source.read_bytes()))
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE116_FOLLOWUP_C_PATCH_REJECTED",
              type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print("STAGE116_PUBLIC_PINNED_FOLLOWUP_C_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
