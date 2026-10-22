#!/usr/bin/env python3
"""Stage105: extend exactly pinned public Stage104 original-disc C68K to 10800 frames.

This modifies ONLY opt-in private vh-private-frame-boot frame cap.
No other emulator mode, media, memory, CD reader or GUI is changed.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from tools.patch_yabause_private_long_frames import instrument_extended_c68k_frames

BEFORE = "frames < 1 || frames > 3600 ||"
AFTER = "frames < 1 || frames > 10800 ||"


def instrument_title_long_run(raw: bytes) -> bytes:
    result = instrument_extended_c68k_frames(raw).decode("utf-8")
    if result.count(BEFORE) != 1 or AFTER in result:
        raise ValueError("pinned Stage104 frame bound not uniquely matched")
    result = result.replace(BEFORE, AFTER, 1)
    if result.count(AFTER) != 1:
        raise ValueError("Stage105 frame bound patch not applied")
    return result.encode("utf-8")


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a=p.parse_args()
    try:
        if (a.source.name!="yui.cpp" or
            a.output.suffix!=".cpp" or a.output.exists() or
            a.source.resolve()==a.output.resolve()):
            raise ValueError("unsafe public source paths")
        with a.output.open("xb") as f:
            f.write(instrument_title_long_run(a.source.read_bytes()))
    except (OSError,ValueError,UnicodeError,TypeError):
        print("STAGE105_PINNED_PRIVATE_LONG_TITLE_REJECTED", file=sys.stderr)
        return 1
    print("STAGE105_PINNED_10800_PRIVATE_FRAME_MODE_READY")
    return 0


if __name__=="__main__":
    sys.exit(main())
