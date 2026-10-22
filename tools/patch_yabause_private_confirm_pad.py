#!/usr/bin/env python3
"""Stage114: add a guarded Saturn A/C menu-confirm pulse to the pinned runner."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_native_start_bit import CONNECT_EXTRA, MODE_END, MODE_START
from tools.patch_yabause_private_start_sequence import (
    EMULATE_START,
    SETUP_SECOND_PULSE,
    instrument_full_private_start_sequence,
)

SETUP_CONFIRM = r'''         /* Stage114: optional A/C confirm pulse, separate from START. */
         const char *vh114_at = getenv("VH_SATURN_CONFIRM_AT_FRAME");
         const char *vh114_button_env = getenv("VH_SATURN_CONFIRM_BUTTON");
         int vh114_confirm_at = -1;
         char vh114_confirm_button = '\0';
         if (vh114_at != NULL || vh114_button_env != NULL)
         {
            if (!vh114_at || !*vh114_at || !vh114_button_env ||
                (vh114_button_env[0] != 'A' && vh114_button_env[0] != 'C') ||
                vh114_button_env[1] != '\0' || vh107_start_at < 0 ||
                vh112_start_at2 >= 0)
               return 240;
            char *endptr114 = NULL;
            long n114 = strtol(vh114_at, &endptr114, 10);
            if (endptr114 == vh114_at || *endptr114 != '\0' ||
                n114 < (long)vh107_start_at + 12L ||
                n114 > (long)frames - 8L)
               return 241;
            vh114_confirm_at = (int)n114;
            vh114_confirm_button = vh114_button_env[0];
         }
'''

CONFIRM_INITIAL = r'''         if (vh114_confirm_at >= 0)
         {
            unsigned char vh114_mask =
               (vh114_confirm_button == 'A') ? 0x04U : 0x02U;
            if ((vh107_pad->padbits[0] & vh114_mask) != vh114_mask)
               return 242;
            if (fprintf(vh109_state_log,
                "VH_PADSTATE initial_confirm_button=%c active_low_bit=1\n",
                vh114_confirm_button) <= 0)
               return 243;
         }
'''

CONFIRM_PRESS = r'''            if (vh114_confirm_at >= 0 && frame == vh114_confirm_at)
            {
               unsigned char vh114_mask =
                  (vh114_confirm_button == 'A') ? 0x04U : 0x02U;
               if (vh114_confirm_button == 'A')
                  PerPadAPressed(vh107_pad);
               else
                  PerPadCPressed(vh107_pad);
               if ((vh107_pad->padbits[0] & vh114_mask) != 0U)
                  return 244;
               if (fprintf(vh107_pad_log,
                   "VH_PAD frame=%d button=%c action=PRESS\n",
                   frame, vh114_confirm_button) <= 0)
                  return 245;
               if (fprintf(vh109_state_log,
                   "VH_PADSTATE frame=%d button=%c active_low_bit=0\n",
                   frame, vh114_confirm_button) <= 0)
                  return 246;
            }
'''

CONFIRM_RELEASE = r'''            if (vh114_confirm_at >= 0 && frame == vh114_confirm_at + 6)
            {
               unsigned char vh114_mask =
                  (vh114_confirm_button == 'A') ? 0x04U : 0x02U;
               if (vh114_confirm_button == 'A')
                  PerPadAReleased(vh107_pad);
               else
                  PerPadCReleased(vh107_pad);
               if ((vh107_pad->padbits[0] & vh114_mask) == 0U)
                  return 247;
               if (fprintf(vh107_pad_log,
                   "VH_PAD frame=%d button=%c action=RELEASE\n",
                   frame, vh114_confirm_button) <= 0)
                  return 248;
               if (fprintf(vh109_state_log,
                   "VH_PADSTATE frame=%d button=%c active_low_bit=1\n",
                   frame, vh114_confirm_button) <= 0)
                  return 249;
            }
'''


def instrument_private_confirm_button(patched: bytes) -> bytes:
    """Add A/C input to the Stage112 branch without altering its START pulses."""
    source = patched.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage112 private frame-boot branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if "VH_SATURN_CONFIRM_AT_FRAME" in mode or "vh114_confirm_at" in mode:
        raise ValueError("Stage114 confirm input already instrumented")
    if mode.count(SETUP_SECOND_PULSE) != 1:
        raise ValueError("Stage112 second-START setup differs from pinned source")
    if mode.count(CONNECT_EXTRA) != 1:
        raise ValueError("Stage109 native pad-state connect anchor differs")
    if mode.count(EMULATE_START) != 1:
        raise ValueError("Stage112 guest-frame execution anchor differs")

    mode = mode.replace(SETUP_SECOND_PULSE, SETUP_SECOND_PULSE + SETUP_CONFIRM, 1)
    mode = mode.replace(CONNECT_EXTRA, CONNECT_EXTRA + CONFIRM_INITIAL, 1)
    mode = mode.replace(EMULATE_START, CONFIRM_PRESS + CONFIRM_RELEASE + EMULATE_START, 1)

    required_once = (
        ("VH_SATURN_CONFIRM_AT_FRAME", 1),
        ("VH_SATURN_CONFIRM_BUTTON", 1),
        ("PerPadAPressed(vh107_pad);", 1),
        ("PerPadAReleased(vh107_pad);", 1),
        ("PerPadCPressed(vh107_pad);", 1),
        ("PerPadCReleased(vh107_pad);", 1),
        ("VH_PADSTATE initial_confirm_button=%c active_low_bit=1", 1),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=0", 1),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=1", 1),
        ("frames > 24000", 1),
    )
    for token, count in required_once:
        if mode.count(token) != count:
            raise ValueError("incomplete Stage114 confirm instrumentation: " + token)
    if (mode.count("YabauseEmulate()") != 1 or
            mode.count("vh109_state_log = fopen") != 1 or
            mode.count("vh107_pad_log = fopen") != 1 or
            mode.count("pad-state.txt") != 1 or
            mode.count("pad-events.txt") != 1):
        raise ValueError("Stage114 altered inherited runner diagnostics")
    if "VH_SATURN_START_AT_FRAME2" not in mode:
        raise ValueError("Stage114 did not preserve Stage112 START setup")
    source = source[:start] + mode + source[end:]
    if source.count("vh101_snapshot(") != 4 or source.count("vh102_snapshot(") != 4:
        raise ValueError("Stage114 did not preserve Stage101/102 diagnostic coverage")
    return source.encode("utf-8")


def instrument_full_private_confirm_sequence(raw: bytes) -> bytes:
    """Compose pinned Stage106/107/109/112 code, then add optional A/C confirm."""
    stage112 = instrument_full_private_start_sequence(raw)
    stage114 = instrument_private_confirm_button(stage112)
    text = stage114.decode("utf-8")
    required = (
        "VH_SATURN_START_AT_FRAME", "VH_SATURN_START_AT_FRAME2",
        "VH_SATURN_CONFIRM_AT_FRAME", "VH_SATURN_CONFIRM_BUTTON",
        "PerPadAPressed(vh107_pad);", "PerPadCPressed(vh107_pad);",
        "pad-state.txt", "video-state.txt", "sh2-window.txt",
        "frames > 24000",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise ValueError("incomplete composed Stage114 pipeline: " + ", ".join(missing))
    return stage114


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
            stream.write(instrument_full_private_confirm_sequence(args.source.read_bytes()))
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE114_PRIVATE_CONFIRM_PATCH_REJECTED",
              type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print("STAGE114_PUBLIC_PINNED_CONFIRM_PAD_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
