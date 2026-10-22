#!/usr/bin/env python3
"""Stage103: one-variable private original Saturn sound-M68K comparison.

All earlier synthetic/dummy modes stay unchanged. The *opt-in* real-disc
game-frame mode substitutes the GPL Yabause C68K interpreter for M68K_DUMMY.
No private Saturn media or game code enters public CI.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from tools.patch_yabause_private_sh2_window import instrument_sh2_window

OLD = "         source_game.m68kcoretype = M68KCORE_DUMMY;"
NEW = "         source_game.m68kcoretype = M68KCORE_C68K;"


def instrument_sound_cpu_runner(raw: bytes) -> bytes:
    s=instrument_sh2_window(raw).decode("utf-8")
    if s.count(OLD) != 1 or NEW in s:
        raise ValueError("pinned original M68K source setting changed")
    s=s.replace(OLD,NEW,1)
    if s.count(NEW)!=1 or s.count("SNDCORE_DUMMY")<1:
        raise ValueError("unexpected sound M68K instrumentation")
    return s.encode("utf-8")


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    try:
        if (a.source.name!="yui.cpp" or
                a.output.suffix!=".cpp" or a.output.exists() or
                a.source.resolve()==a.output.resolve()):
            raise ValueError("unsafe public runner paths")
        with a.output.open("xb") as out:
            out.write(instrument_sound_cpu_runner(a.source.read_bytes()))
    except (OSError,ValueError,TypeError,UnicodeError):
        print("STAGE103_PINNED_SOUND_CPU_EXPERIMENT_REJECTED",file=sys.stderr)
        return 1
    print("STAGE103_PUBLIC_PINNED_YABAUSE_C68K_FRAME_MODE_PREPARED")
    return 0


if __name__=="__main__":
    sys.exit(main())
