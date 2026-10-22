#!/usr/bin/env python3
"""Stage112: add a second guarded START pulse and extend the private run window.

Applies only to the already-pinned Stage109 real Yabause source after its
C68K, real ISOCD, framebuffer, and native active-low pad instrumentation.
Public CI uses only invented media; the resulting public GPL executable can
later be invoked privately with the user's own disc.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_pad import SETUP, PRESS_ANCHOR, RELEASE_ANCHOR

MODE_MAX = re.compile(r"frames > (?:600|12000|13200)\b")
PRESS_START = '            if (vh107_start_at >= 0 && frame == vh107_start_at)\n            {'
RELEASE_START = '            if (vh107_start_at >= 0 && frame == vh107_start_at + 6)\n            {'
EMULATE_START = '            if (YabauseEmulate() != 0)'
SETUP_SECOND_PULSE = r'''         /* Stage112: optional second START pulse after the first menu opens. */
         const char *vh112_at2 = getenv("VH_SATURN_START_AT_FRAME2");
         int vh112_start_at2 = -1;
         if (vh112_at2 && *vh112_at2)
         {
            char *endptr2 = NULL;
            long n2 = strtol(vh112_at2, &endptr2, 10);
            if (vh107_start_at < 0 || endptr2 == vh112_at2 ||
                *endptr2 != '\0' || n2 < (long)vh107_start_at + 12L ||
                n2 > (long)frames - 8L)
               return 239;
            vh112_start_at2 = (int)n2;
         }
'''


def instrument_private_start_sequence(raw: bytes) -> bytes:
    source = raw.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage109 private frame-boot branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if "VH_SATURN_START_AT_FRAME2" in mode or "vh112_start_at2" in mode:
        raise ValueError("Stage112 second pulse already instrumented")

    # Keep the Stage107 first pulse unchanged; add the optional second one
    # after its strict first-pulse parser has finished.
    setup_end = "            vh107_start_at = (int)n;\n         }\n"
    if mode.count(SETUP) != 1 or mode.count(setup_end) != 1:
        raise ValueError("Stage107 first-pulse setup differs from pinned source")
    mode = mode.replace(setup_end, setup_end + SETUP_SECOND_PULSE, 1)

    press_pos = mode.find(PRESS_START)
    release_pos = mode.find(RELEASE_START)
    emulate_pos = mode.find(EMULATE_START)
    if (min(press_pos, release_pos, emulate_pos) < 0 or
            not (press_pos < release_pos < emulate_pos) or
            mode.count(PRESS_START) != 1 or mode.count(RELEASE_START) != 1 or
            mode.count(EMULATE_START) != 1):
        raise ValueError("pinned Stage109 input loop anchors differ")
    press_block = mode[press_pos:release_pos]
    release_block = mode[release_pos:emulate_pos]
    if (press_block.count("PerPadStartPressed(vh107_pad);") != 1 or
            release_block.count("PerPadStartReleased(vh107_pad);") != 1 or
            "VH_PAD frame=%d button=START action=PRESS" not in press_block or
            "VH_PAD frame=%d button=START action=RELEASE" not in release_block or
            "VH_PADSTATE frame=%d start_bit=0" not in press_block or
            "VH_PADSTATE frame=%d start_bit=1" not in release_block):
        raise ValueError("native controller and pad-state witnesses missing")

    second_press = press_block.replace("vh107_start_at", "vh112_start_at2")
    second_release = release_block.replace("vh107_start_at", "vh112_start_at2")
    if second_press.count("vh112_start_at2") != 1 or second_release.count("vh112_start_at2") != 2:
        raise ValueError("second-pulse loop did not remain frame-indexed")
    # The new checks run before YabauseEmulate, exactly like the first pulse.
    mode = mode[:emulate_pos] + second_press + second_release + mode[emulate_pos:]

    mode, bound_count = MODE_MAX.subn("frames > 24000", mode)
    if bound_count < 1:
        raise ValueError("no recognized Stage109 bounded frame maximum")
    if (mode.count("VH_SATURN_START_AT_FRAME2") != 1 or
            mode.count("PerPadStartPressed(vh107_pad);") != 2 or
            mode.count("PerPadStartReleased(vh107_pad);") != 2 or
            mode.count("frames > 24000") < bound_count or
            mode.count("YabauseEmulate()") != 1):
        raise ValueError("incomplete two-pulse 24000-frame mode")
    source = source[:start] + mode + source[end:]
    return source.encode("utf-8")


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
            stream.write(instrument_private_start_sequence(args.source.read_bytes()))
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        print("STAGE112_PRIVATE_START_SEQUENCE_PATCH_REJECTED",
              type(exc).__name__, file=sys.stderr)
        return 1
    print("STAGE112_PUBLIC_YABAUSE_DUAL_START_PATCH_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
