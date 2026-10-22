#!/usr/bin/env python3
"""Stage117: add one optional, guarded third C pulse to advance the prologue."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_second_confirm import (
    CONFIRM_SETUP_END,
    SETUP_CONFIRM2,
    instrument_full_private_second_confirm,
)
from tools.patch_yabause_private_start_sequence import EMULATE_START

SETUP_CONFIRM3_ANCHOR = "            vh116_confirm_at2 = (int)n116;\n         }\n"

SETUP_CONFIRM3 = r'''         /* Stage117: optional third C pulse for the opening dialogue. */
         const char *vh117_at3 = getenv("VH_SATURN_CONFIRM_AT_FRAME3");
         int vh117_confirm_at3 = -1;
         if (vh117_at3 != NULL)
         {
            if (!*vh117_at3 || vh116_confirm_at2 < 0 ||
                vh114_confirm_button != 'C')
               return 260;
            char *endptr117 = NULL;
            long n117 = strtol(vh117_at3, &endptr117, 10);
            if (endptr117 == vh117_at3 || *endptr117 != '\0' ||
                n117 < (long)vh116_confirm_at2 + 12L ||
                n117 > (long)frames - 8L)
               return 261;
            vh117_confirm_at3 = (int)n117;
         }
'''

CONFIRM3_PRESS = r'''            if (vh117_confirm_at3 >= 0 && frame == vh117_confirm_at3)
            {
               const unsigned char vh117_mask = 0x02U;
               if ((vh107_pad->padbits[0] & vh117_mask) == 0U)
                  return 262;
               PerPadCPressed(vh107_pad);
               if ((vh107_pad->padbits[0] & vh117_mask) != 0U)
                  return 263;
               if (fprintf(vh107_pad_log,
                   "VH_PAD frame=%d button=%c action=PRESS\n",
                   frame, 'C') <= 0)
                  return 264;
               if (fprintf(vh109_state_log,
                   "VH_PADSTATE frame=%d button=%c active_low_bit=0\n",
                   frame, 'C') <= 0)
                  return 265;
            }
'''

CONFIRM3_RELEASE = r'''            if (vh117_confirm_at3 >= 0 && frame == vh117_confirm_at3 + 6)
            {
               const unsigned char vh117_mask = 0x02U;
               if ((vh107_pad->padbits[0] & vh117_mask) != 0U)
                  return 266;
               PerPadCReleased(vh107_pad);
               if ((vh107_pad->padbits[0] & vh117_mask) == 0U)
                  return 267;
               if (fprintf(vh107_pad_log,
                   "VH_PAD frame=%d button=%c action=RELEASE\n",
                   frame, 'C') <= 0)
                  return 268;
               if (fprintf(vh109_state_log,
                   "VH_PADSTATE frame=%d button=%c active_low_bit=1\n",
                   frame, 'C') <= 0)
                  return 269;
            }
'''


def instrument_private_third_confirm(patched: bytes) -> bytes:
    source = patched.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage116 48,000-frame runner branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if "frames > 48000" not in mode:
        raise ValueError("Stage117 requires the Stage116 48,000-frame cap")
    if "VH_SATURN_CONFIRM_AT_FRAME3" in mode or "vh117_confirm_at3" in mode:
        raise ValueError("Stage117 third confirm pulse already instrumented")
    if mode.count(SETUP_CONFIRM2) != 1 or mode.count(SETUP_CONFIRM3_ANCHOR) != 1:
        raise ValueError("Stage116 second-confirm setup anchor differs")
    if mode.count(EMULATE_START) != 1:
        raise ValueError("Stage116 guest-frame execution anchor differs")

    mode = mode.replace(
        SETUP_CONFIRM3_ANCHOR,
        SETUP_CONFIRM3_ANCHOR + SETUP_CONFIRM3,
        1,
    )
    mode = mode.replace(
        EMULATE_START,
        CONFIRM3_PRESS + CONFIRM3_RELEASE + EMULATE_START,
        1,
    )
    required = (
        ("VH_SATURN_CONFIRM_AT_FRAME3", 1),
        ("vh117_confirm_at3", 6),
        ("PerPadCPressed(vh107_pad);", 3),
        ("PerPadCReleased(vh107_pad);", 3),
        ("VH_PAD frame=%d button=%c action=PRESS", 3),
        ("VH_PAD frame=%d button=%c action=RELEASE", 3),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=0", 3),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=1", 3),
        ("frames > 48000", 1),
    )
    for token, count in required:
        if mode.count(token) != count:
            raise ValueError("incomplete Stage117 third-confirm instrumentation: " + token)
    if mode.count("YabauseEmulate()") != 1:
        raise ValueError("Stage117 changed the inherited guest-frame loop")
    source = source[:start] + mode + source[end:]
    if source.count("vh101_snapshot(") != 4 or source.count("vh102_snapshot(") != 4:
        raise ValueError("Stage117 changed inherited video/SH2 diagnostics")
    return source.encode("utf-8")


def instrument_full_private_third_confirm(raw: bytes) -> bytes:
    stage116 = instrument_full_private_second_confirm(raw)
    stage117 = instrument_private_third_confirm(stage116)
    text = stage117.decode("utf-8")
    for token in (
        "VH_SATURN_CONFIRM_AT_FRAME",
        "VH_SATURN_CONFIRM_AT_FRAME2",
        "VH_SATURN_CONFIRM_AT_FRAME3",
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
        if (
            args.source.name != "yui.cpp"
            or args.output.suffix != ".cpp"
            or args.output.exists()
            or args.source.resolve() == args.output.resolve()
        ):
            raise ValueError("unsafe pinned public Yabause source paths")
        with args.output.open("xb") as stream:
            stream.write(instrument_full_private_third_confirm(args.source.read_bytes()))
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE117_THIRD_CONFIRM_PATCH_REJECTED",
              type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print("STAGE117_THIRD_CONFIRM_RUNNER_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
