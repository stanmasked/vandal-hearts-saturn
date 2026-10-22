#!/usr/bin/env python3
"""Stage116: add one optional, guarded second C pulse to advance prologue dialogue."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_long_window import instrument_full_private_long_window
from tools.patch_yabause_private_start_sequence import EMULATE_START

CONFIRM_SETUP_END = "            vh114_confirm_button = vh114_button_env[0];\n         }\n"

SETUP_CONFIRM2 = r'''         /* Stage116: optional second C pulse for the opening dialogue. */
         const char *vh116_at2 = getenv("VH_SATURN_CONFIRM_AT_FRAME2");
         int vh116_confirm_at2 = -1;
         if (vh116_at2 != NULL)
         {
            if (!*vh116_at2 || vh114_confirm_at < 0 ||
                vh114_confirm_button != 'C' || vh112_start_at2 >= 0)
               return 250;
            char *endptr116 = NULL;
            long n116 = strtol(vh116_at2, &endptr116, 10);
            if (endptr116 == vh116_at2 || *endptr116 != '\0' ||
                n116 < (long)vh114_confirm_at + 12L ||
                n116 > (long)frames - 8L)
               return 251;
            vh116_confirm_at2 = (int)n116;
         }
'''

CONFIRM2_PRESS = r'''            if (vh116_confirm_at2 >= 0 && frame == vh116_confirm_at2)
            {
               const unsigned char vh116_mask = 0x02U;
               if ((vh107_pad->padbits[0] & vh116_mask) == 0U)
                  return 252;
               PerPadCPressed(vh107_pad);
               if ((vh107_pad->padbits[0] & vh116_mask) != 0U)
                  return 253;
               if (fprintf(vh107_pad_log,
                   "VH_PAD frame=%d button=%c action=PRESS\n",
                   frame, 'C') <= 0)
                  return 254;
               if (fprintf(vh109_state_log,
                   "VH_PADSTATE frame=%d button=%c active_low_bit=0\n",
                   frame, 'C') <= 0)
                  return 255;
            }
'''

CONFIRM2_RELEASE = r'''            if (vh116_confirm_at2 >= 0 && frame == vh116_confirm_at2 + 6)
            {
               const unsigned char vh116_mask = 0x02U;
               if ((vh107_pad->padbits[0] & vh116_mask) != 0U)
                  return 256;
               PerPadCReleased(vh107_pad);
               if ((vh107_pad->padbits[0] & vh116_mask) == 0U)
                  return 257;
               if (fprintf(vh107_pad_log,
                   "VH_PAD frame=%d button=%c action=RELEASE\n",
                   frame, 'C') <= 0)
                  return 258;
               if (fprintf(vh109_state_log,
                   "VH_PADSTATE frame=%d button=%c active_low_bit=1\n",
                   frame, 'C') <= 0)
                  return 259;
            }
'''


def instrument_private_second_confirm(patched: bytes) -> bytes:
    source = patched.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage115 48,000-frame runner branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if "frames > 48000" not in mode:
        raise ValueError("Stage116 requires the Stage115 48,000-frame cap")
    if "VH_SATURN_CONFIRM_AT_FRAME2" in mode or "vh116_confirm_at2" in mode:
        raise ValueError("Stage116 second confirm pulse already instrumented")
    if mode.count(CONFIRM_SETUP_END) != 1:
        raise ValueError("Stage114 first-confirm setup anchor differs")
    if mode.count(EMULATE_START) != 1:
        raise ValueError("Stage115 guest-frame execution anchor differs")

    mode = mode.replace(CONFIRM_SETUP_END, CONFIRM_SETUP_END + SETUP_CONFIRM2, 1)
    mode = mode.replace(EMULATE_START, CONFIRM2_PRESS + CONFIRM2_RELEASE + EMULATE_START, 1)
    required_once = (
        ("VH_SATURN_CONFIRM_AT_FRAME2", 1),
        ("vh116_confirm_at2", 4),
        ("PerPadCPressed(vh107_pad);", 2),
        ("PerPadCReleased(vh107_pad);", 2),
        ("VH_PAD frame=%d button=%c action=PRESS", 2),
        ("VH_PAD frame=%d button=%c action=RELEASE", 2),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=0", 2),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=1", 2),
        ("frames > 48000", 1),
    )
    for token, count in required_once:
        if mode.count(token) != count:
            raise ValueError("incomplete Stage116 second-confirm instrumentation: " + token)
    if mode.count("YabauseEmulate()") != 1:
        raise ValueError("Stage116 changed the inherited guest-frame loop")
    source = source[:start] + mode + source[end:]
    if source.count("vh101_snapshot(") != 4 or source.count("vh102_snapshot(") != 4:
        raise ValueError("Stage116 changed inherited video/SH2 diagnostics")
    return source.encode("utf-8")


def instrument_full_private_second_confirm(raw: bytes) -> bytes:
    stage115 = instrument_full_private_long_window(raw)
    stage116 = instrument_private_second_confirm(stage115)
    text = stage116.decode("utf-8")
    for token in (
        "VH_SATURN_CONFIRM_AT_FRAME",
        "VH_SATURN_CONFIRM_AT_FRAME2",
        "VH_SATURN_CONFIRM_BUTTON",
        "frames > 48000",
        "frames.stats",
        "video-state.txt",
        "sh2-window.txt",
        "pad-state.txt",
    ):
        if token not in text:
            raise ValueError("incomplete composed Stage116 runner: " + token)
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
            stream.write(instrument_full_private_second_confirm(args.source.read_bytes()))
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE116_SECOND_CONFIRM_PATCH_REJECTED",
              type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print("STAGE116_SECOND_CONFIRM_RUNNER_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
