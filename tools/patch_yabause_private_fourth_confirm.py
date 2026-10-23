#!/usr/bin/env python3
"""Stage118: add one optional, guarded fourth C pulse after Stage117."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_third_confirm import instrument_full_private_third_confirm
from tools.patch_yabause_private_start_sequence import EMULATE_START

THIRD_SETUP_END = (
    "         vh117_confirm_at3 = (int)n117;\n"
    "         vh117_confirm3_enabled = (vh117_enable3[0] == '1') ? 1 : 0;\n"
)

SETUP_CONFIRM4 = r'''         /* Stage118: identical scheduled fourth-C frame in both paired runs. */
         const char *vh118_at4 = getenv("VH_SATURN_CONFIRM_AT_FRAME4");
         const char *vh118_enable4 = getenv("VH_SATURN_CONFIRM4_ENABLED");
         int vh118_confirm_at4 = -1;
         int vh118_confirm4_enabled = -1;
         if (vh118_at4 == NULL || vh118_enable4 == NULL || !*vh118_at4 ||
             vh117_confirm_at3 < 0 || vh117_confirm3_enabled != 1)
            return 272;
         char *endptr118 = NULL;
         long n118 = strtol(vh118_at4, &endptr118, 10);
         if (endptr118 == vh118_at4 || *endptr118 != '\0' ||
             n118 < (long)vh117_confirm_at3 + 12L ||
             n118 > (long)frames - 8L)
            return 273;
         if (vh118_enable4[1] != '\0' ||
             (vh118_enable4[0] != '0' && vh118_enable4[0] != '1'))
            return 274;
         vh118_confirm_at4 = (int)n118;
         vh118_confirm4_enabled = (vh118_enable4[0] == '1') ? 1 : 0;
'''

CONFIRM4_PRESS = r'''            if (vh118_confirm_at4 >= 0 && frame == vh118_confirm_at4)
            {
               if (vh118_confirm4_enabled)
               {
                  const unsigned char vh118_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh118_mask) == 0U)
                     return 275;
                  PerPadCPressed(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh118_mask) != 0U)
                     return 276;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=PRESS\n",
                      frame, 'C') <= 0)
                     return 277;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=0\n",
                      frame, 'C') <= 0)
                     return 278;
               }
            }
'''

CONFIRM4_RELEASE = r'''            if (vh118_confirm_at4 >= 0 && frame == vh118_confirm_at4 + 6)
            {
               if (vh118_confirm4_enabled)
               {
                  const unsigned char vh118_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh118_mask) != 0U)
                     return 279;
                  PerPadCReleased(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh118_mask) == 0U)
                     return 280;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=RELEASE\n",
                      frame, 'C') <= 0)
                     return 281;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=1\n",
                      frame, 'C') <= 0)
                     return 282;
               }
            }
'''


def instrument_private_fourth_confirm(patched: bytes) -> bytes:
    source = patched.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage117 48,000-frame runner branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if "frames > 48000" not in mode:
        raise ValueError("Stage118 requires the Stage115 48,000-frame cap")
    if ("VH_SATURN_CONFIRM_AT_FRAME4" in mode or
            "vh118_confirm_at4" in mode):
        raise ValueError("Stage118 fourth confirm pulse already instrumented")
    if mode.count(THIRD_SETUP_END) != 1:
        raise ValueError("Stage117 third-confirm setup anchor differs")
    if mode.count(EMULATE_START) != 1:
        raise ValueError("Stage117 guest-frame execution anchor differs")

    mode = mode.replace(THIRD_SETUP_END,
                        THIRD_SETUP_END + SETUP_CONFIRM4, 1)
    mode = mode.replace(EMULATE_START,
                        CONFIRM4_PRESS + CONFIRM4_RELEASE + EMULATE_START, 1)
    required = (
        ("VH_SATURN_CONFIRM_AT_FRAME4", 1),
        ("VH_SATURN_CONFIRM4_ENABLED", 1),
        ("vh118_confirm_at4", 6),
        ("vh118_confirm4_enabled", 4),
        ("PerPadCPressed(vh107_pad);", 4),
        ("PerPadCReleased(vh107_pad);", 4),
        ("VH_PAD frame=%d button=%c action=PRESS", 4),
        ("VH_PAD frame=%d button=%c action=RELEASE", 4),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=0", 4),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=1", 4),
        ("frames > 48000", 1),
    )
    for token, count in required:
        if mode.count(token) != count:
            raise ValueError("incomplete Stage118 fourth-confirm instrumentation: " + token)
    if mode.count("YabauseEmulate()") != 1:
        raise ValueError("Stage118 changed the inherited guest-frame loop")
    source = source[:start] + mode + source[end:]
    if source.count("vh101_snapshot(") != 4 or source.count("vh102_snapshot(") != 4:
        raise ValueError("Stage118 changed inherited video/SH2 diagnostics")
    return source.encode("utf-8")


def instrument_full_private_fourth_confirm(raw: bytes) -> bytes:
    stage117 = instrument_full_private_third_confirm(raw)
    stage118 = instrument_private_fourth_confirm(stage117)
    text = stage118.decode("utf-8")
    for token in (
        "VH_SATURN_START_AT_FRAME",
        "VH_SATURN_CONFIRM_AT_FRAME",
        "VH_SATURN_CONFIRM_AT_FRAME2",
        "VH_SATURN_CONFIRM2_ENABLED",
        "VH_SATURN_CONFIRM_AT_FRAME3",
        "VH_SATURN_CONFIRM3_ENABLED",
        "VH_SATURN_CONFIRM_AT_FRAME4",
        "VH_SATURN_CONFIRM4_ENABLED",
        "VH_SATURN_CONFIRM_BUTTON",
        "frames > 48000",
        "frames.stats",
        "video-state.txt",
        "sh2-window.txt",
        "pad-state.txt",
    ):
        if token not in text:
            raise ValueError("incomplete composed Stage118 runner: " + token)
    return stage118


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
            stream.write(instrument_full_private_fourth_confirm(args.source.read_bytes()))
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE118_FOURTH_CONFIRM_PATCH_REJECTED",
              type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print("STAGE118_FOURTH_CONFIRM_RUNNER_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
