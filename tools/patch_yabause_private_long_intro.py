#!/usr/bin/env python3
"""Stage105: extend bounded *private* original C68K/Yabause run to 9000 frames.

Uses the identical upstream-verified game core, all public smoke modes,
and local-only PNG/FAD/VDP/SH2 evidence from Stage104. Does not auto-press
game buttons or mislabel an intro video as a battle/title menu.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from tools.patch_yabause_private_title_progress import instrument_title_progress

OLD = "             frames < 1 || frames > 3600 ||"
NEW = "             frames < 1 || frames > 9000 ||"


def instrument_long_intro(raw: bytes) -> bytes:
    s=instrument_title_progress(raw).decode("utf-8")
    if s.count(OLD)!=1 or NEW in s:
        raise ValueError("pinned Stage104 original movie cap changed")
    s=s.replace(OLD,NEW,1)
    if (s.count(NEW)!=1 or
            s.count("source_game.m68kcoretype = M68KCORE_C68K;")!=1 or
            s.count("progress % 120 == 0")!=1):
        raise ValueError("unexpected private Yabause long-run changes")
    return s.encode("utf-8")


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    try:
        if (a.source.name!="yui.cpp" or a.output.suffix!=".cpp" or
                a.source.resolve()==a.output.resolve() or a.output.exists()):
            raise ValueError("unsafe public runner paths")
        with a.output.open("xb") as f:
            f.write(instrument_long_intro(a.source.read_bytes()))
    except (ValueError,OSError,TypeError,UnicodeError):
        print("STAGE105_PINNED_PRIVATE_LONG_RUN_REJECTED",file=sys.stderr)
        return 1
    print("STAGE105_PINNED_PUBLIC_YABAUSE_9000_FRAME_CAP_READY")
    return 0


if __name__=="__main__":
    sys.exit(main())
