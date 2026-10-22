#!/usr/bin/env python3
"""Stage104: extend private original-disc C68K Yabause frame timeline to 3600.

Input must match pinned Stage103 public Yabause source. Only game-private
capture mode changes; every synthetic and diagnostic mode stays unchanged.
No copyrighted game data or screenshots enter GitHub Actions.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_private_c68k_experiment import (
    instrument_sound_cpu_runner,
)

OLD = "frames < 1 || frames > 600 ||"
NEW = "frames < 1 || frames > 3600 ||"
CHECKPOINT = "if (progress % 120 == 0)"
GAME_MODE = 'strcmp(argv[1], "vh-private-frame-boot")'


def instrument_extended_c68k_frames(original: bytes) -> bytes:
    source = instrument_sound_cpu_runner(original).decode("utf-8")
    if (
        source.count(OLD) != 1
        or NEW in source
        or source.count(CHECKPOINT) != 1
        or source.count(GAME_MODE) != 2
        or source.count("source_game.m68kcoretype = M68KCORE_C68K;") != 1
    ):
        raise ValueError("unexpected pinned Stage103 frame-code layout")
    source = source.replace(OLD, NEW, 1)
    if source.count(NEW) != 1 or source.count("YabauseEmulate()") != 2:
        raise ValueError("Stage104 C68K frame bound patch incomplete")
    return source.encode("utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        if (
            args.source.resolve() == args.output.resolve()
            or args.output.exists()
            or args.source.name != "yui.cpp"
            or args.output.suffix != ".cpp"
        ):
            raise ValueError("invalid pinned upstream file paths")
        data = instrument_extended_c68k_frames(args.source.read_bytes())
        with args.output.open("xb") as destination:
            destination.write(data)
    except (OSError, ValueError, TypeError, UnicodeError):
        print("STAGE104_PINNED_C68K_LONG_CAPTURE_REJECTED", file=sys.stderr)
        return 1
    print("STAGE104_PINNED_C68K_3600_FRAME_MODE_PREPARED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
