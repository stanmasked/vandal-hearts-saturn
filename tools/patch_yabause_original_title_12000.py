#!/usr/bin/env python3
"""Stage106: exact public pinned Yabause C68K original title visibility cap=12000.

Only the existing opt-in, private vh-private-frame-boot bound changes.
All inherited real Yabause CD, SH2, M68K, VDP, frame and privacy
instrumentation remains unchanged. Public GitHub CI contains no game media.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from tools.patch_yabause_private_title_10800 import instrument_title_long_run

BEFORE = "frames < 1 || frames > 10800 ||"
AFTER = "frames < 1 || frames > 12000 ||"


def instrument_original_title_12000(raw: bytes) -> bytes:
    c=instrument_title_long_run(raw).decode("utf-8")
    if c.count(BEFORE)!=1 or AFTER in c:
        raise ValueError("unpinned or changed Stage105 runner")
    c=c.replace(BEFORE,AFTER,1)
    if c.count(AFTER)!=1 or c.count("M68KCORE_C68K")!=1:
        raise ValueError("Stage106 title stage failed closed")
    return c.encode("utf-8")


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    try:
        if (a.source.name!="yui.cpp" or a.output.suffix!=".cpp" or
                a.output.exists() or a.source.resolve()==a.output.resolve()):
            raise ValueError("unsafe instrumented public runner path")
        with a.output.open("xb") as out:out.write(instrument_original_title_12000(a.source.read_bytes()))
    except (OSError,ValueError,UnicodeError,TypeError):
        print("STAGE106_PINNED_TITLE_EXECUTABLE_REJECTED",file=sys.stderr)
        return 1
    print("STAGE106_PUBLIC_PINNED_YABAUSE_12000_TITLE_MODE_READY")
    return 0


if __name__=="__main__":
    sys.exit(main())
