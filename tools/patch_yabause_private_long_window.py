#!/usr/bin/env python3
"""Stage115: extend the pinned private Yabause frame window to 48,000 frames."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_native_start_bit import MODE_END, MODE_START
from tools.patch_yabause_private_confirm_pad import instrument_full_private_confirm_sequence


def instrument_private_48000_frame_window(patched: bytes) -> bytes:
    source = patched.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage114 private frame-boot branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if "frames > 48000" in mode:
        raise ValueError("Stage115 48,000-frame bound already applied")
    if mode.count("frames > 24000") != 1:
        raise ValueError("Stage114 24,000-frame fail-closed bound differs")
    mode = mode.replace("frames > 24000", "frames > 48000", 1)
    required = (
        "frames > 48000",
        "VH_SATURN_CONFIRM_AT_FRAME",
        "VH_SATURN_CONFIRM_BUTTON",
        "PerPadAPressed(vh107_pad);",
        "PerPadCPressed(vh107_pad);",
        "VH_PADSTATE initial_confirm_button=%c active_low_bit=1",
        "video-state.txt",
        "sh2-window.txt",
        "pad-state.txt",
    )
    for token in required:
        if token not in mode:
            raise ValueError("incomplete Stage115 long-window runner: " + token)
    if "frames > 24000" in mode:
        raise ValueError("Stage115 left the shorter frame cap active")
    if mode.count("YabauseEmulate()") != 1:
        raise ValueError("Stage115 changed the inherited guest-frame loop")
    source = source[:start] + mode + source[end:]
    if source.count("vh101_snapshot(") != 4 or source.count("vh102_snapshot(") != 4:
        raise ValueError("Stage115 did not preserve inherited diagnostic coverage")
    return source.encode("utf-8")


def instrument_full_private_long_window(raw: bytes) -> bytes:
    stage114 = instrument_full_private_confirm_sequence(raw)
    stage115 = instrument_private_48000_frame_window(stage114)
    text = stage115.decode("utf-8")
    required = (
        "VH_SATURN_START_AT_FRAME",
        "VH_SATURN_CONFIRM_AT_FRAME",
        "VH_SATURN_CONFIRM_BUTTON",
        "PerPadCPressed(vh107_pad);",
        "frames > 48000",
        "video-state.txt",
        "sh2-window.txt",
        "pad-state.txt",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise ValueError("incomplete composed Stage115 pipeline: " + ", ".join(missing))
    return stage115


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
            stream.write(instrument_full_private_long_window(args.source.read_bytes()))
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE115_LONG_WINDOW_PATCH_REJECTED",
              type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print("STAGE115_PUBLIC_PINNED_48000_FRAME_WINDOW_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
