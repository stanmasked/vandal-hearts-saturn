#!/usr/bin/env python3
"""Stage104: let the privately owned original Saturn disc progress past splash.

Increases opt-in real-game bounded frame window to 3600, keeping C68K/SH2,
ISOCD, HLE BIOS and all public synthetic regression modes unchanged.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from tools.patch_yabause_private_c68k_experiment import instrument_sound_cpu_runner

OLD = "             frames < 1 || frames > 600 ||"
NEW = "             frames < 1 || frames > 3600 ||"


def instrument_title_progress(raw: bytes) -> bytes:
    s=instrument_sound_cpu_runner(raw).decode("utf-8")
    if s.count(OLD)!=1 or NEW in s:
        raise ValueError("pinned Stage103 original frame bound differs")
    s=s.replace(OLD,NEW,1)
    if s.count(NEW)!=1 or s.count("source_game.m68kcoretype = M68KCORE_C68K;")!=1:
        raise ValueError("Stage104 long original game mode not isolated")
    return s.encode("utf-8")


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    try:
        if (a.source.name!="yui.cpp" or
            a.output.suffix!=".cpp" or a.output.exists() or
            a.output.resolve()==a.source.resolve()):
            raise ValueError("unsafe source/output")
        with a.output.open("xb") as f:
            f.write(instrument_title_progress(a.source.read_bytes()))
    except (OSError,ValueError,TypeError,UnicodeError):
        print("STAGE104_PRIVATE_TITLE_PROGRESS_PATCH_REJECTED",file=sys.stderr)
        return 1
    print("STAGE104_PUBLIC_YABAUSE_LONG_PRIVATE_FRAME_MODE_PREPARED")
    return 0


if __name__=="__main__":
    sys.exit(main())
