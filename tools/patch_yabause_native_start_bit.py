#!/usr/bin/env python3
"""Stage109: observe the real historical Yabause pad's active-low START bit.

Adds a private numeric-only pad-state receipt to Stage107's genuine C68K
Saturn controller mode. This proves *host peripheral memory* changed when
the emulator API was called, not that guest Saturn software sampled START.
No original media or screenshots are read, uploaded or embedded.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_private_start_pad import (
    CONNECT, FINALIZE, instrument_gamepad_start,
)

MODE_START = '      if (strcmp(argv[1], "vh-private-frame-boot") == 0)\n      {'
MODE_END = (
    '         puts("STAGE99_REAL_YABAUSE_BOUND_FRAMES_PASS");\n'
    '         return 0;\n      }'
)
SETUP_ANCHOR = '         FILE *vh107_pad_log = NULL;\n'
PRESS_ANCHOR = '               PerPadStartPressed(vh107_pad);\n'
RELEASE_ANCHOR = '               PerPadStartReleased(vh107_pad);\n'
PRESS_BIT = 0x08

SETUP_EXTRA = r'''         char vh109_state_path[1024];
         if (snprintf(vh109_state_path, sizeof(vh109_state_path),
                      "%s/pad-state.txt", private_dir)
             >= (int)sizeof(vh109_state_path))
            return 230;
         FILE *vh109_state_log = NULL;
'''

CONNECT_EXTRA = r'''         /* Real pinned peripheral.c initializes this pad bit to 1. */
         if ((vh107_pad->padbits[0] & 0x08U) == 0U)
            return 231;
         vh109_state_log = fopen(vh109_state_path, "wx");
         if (!vh109_state_log)
            return 232;
         if (fprintf(vh109_state_log,
                     "VH_PADSTATE initial_start_bit=1\n") <= 0)
            return 233;
'''

PRESS_EXTRA = r'''               /* Bit 3 is active-low on a genuine Saturn digital pad. */
               if ((vh107_pad->padbits[0] & 0x08U) != 0U)
                  return 234;
               if (fprintf(vh109_state_log,
                           "VH_PADSTATE frame=%d start_bit=0\n", frame) <= 0)
                  return 235;
'''

RELEASE_EXTRA = r'''               if ((vh107_pad->padbits[0] & 0x08U) == 0U)
                  return 236;
               if (fprintf(vh109_state_log,
                           "VH_PADSTATE frame=%d start_bit=1\n", frame) <= 0)
                  return 237;
'''

FINALIZE_EXTRA = r'''         if (!vh109_state_log ||
             fprintf(vh109_state_log,
                     "VH_PADSTATE mode=%d completed_frames=%d\n",
                     vh107_start_at >= 0 ? 1 : 0, progress) <= 0 ||
             fclose(vh109_state_log) != 0)
            return 238;
'''


def instrument_native_start_bit_on_patched_source(patched: bytes) -> bytes:
    """Add Stage109's native pad-bit witness without rebuilding earlier stages."""
    source = patched.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned original Saturn command branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if "vh109_state_log" in mode:
        raise ValueError("duplicate START bit instrumentation")
    replacements = [
        (SETUP_ANCHOR, SETUP_ANCHOR + SETUP_EXTRA),
        (CONNECT, CONNECT + CONNECT_EXTRA),
        (PRESS_ANCHOR, PRESS_ANCHOR + PRESS_EXTRA),
        (RELEASE_ANCHOR, RELEASE_ANCHOR + RELEASE_EXTRA),
        (FINALIZE, FINALIZE_EXTRA + FINALIZE),
    ]
    for old, new in replacements:
        if mode.count(old) != 1:
            raise ValueError("Stage107 pinned controller patch changed: " + old[:32])
        mode = mode.replace(old, new, 1)
    source = source[:start] + mode + source[end:]
    if (source.count("VH_PADSTATE") != 4 or
            source.count("pad-state.txt") != 1 or
            source.count("vh109_state_log = fopen") != 1 or
            source.count("YabauseEmulate()") != 2):
        raise ValueError("incomplete native active-low START bit witness")
    return source.encode("utf-8")


def instrument_native_start_bit(raw: bytes) -> bytes:
    """Build the historical Stage109 chain from the pinned original source."""
    return instrument_native_start_bit_on_patched_source(
        instrument_gamepad_start(raw)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if (args.source.name != "yui.cpp" or
                args.output.suffix != ".cpp" or args.output.exists() or
                args.source.resolve() == args.output.resolve()):
            raise ValueError("unsafe pinned public source paths")
        with args.output.open("xb") as stream:
            stream.write(instrument_native_start_bit(args.source.read_bytes()))
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE109_PINNED_NATIVE_START_STATE_REJECTED",
              type(exc).__name__, file=sys.stderr)
        return 1
    print("STAGE109_PINNED_NATIVE_PAD_START_BIT_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
