#!/usr/bin/env python3
"""Stage89: opt-in public runner mode for real two-file Saturn-shaped CUE."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

from tools.patch_yabause_real_cue import (
    CUE_CHECK, STAGE88_CONDITION, instrument_runner as stage88_runner,
)

MODE = "vh-two-file-cue-read"
RECEIPT = "STAGE89_REAL_YABAUSE_SPLIT_CUE_AUDIO_PASS"
STAGE89_CONDITION = STAGE88_CONDITION.replace(
    '(argc == 3 && strcmp(argv[1], "vh-exact-cue-read") == 0))',
    '(argc == 3 && (strcmp(argv[1], "vh-exact-cue-read") == 0 || '
    'strcmp(argv[1], "vh-two-file-cue-read") == 0)))',
)

SPLIT_CHECK = r'''      if (strcmp(argv[1], "vh-two-file-cue-read") == 0)
      {
         const char *gate_path = getenv("VH_SATURN_CAPTURE_GATE");
         unsigned char sector[2448] = {0};
         u32 toc[102] = {0};
         if (argc != 3 || !gate_path || !gate_path[0])
         {
            YabauseDeInit();
            return 107;
         }
         if (ISOCD.Init(argv[2]) != 0)
         {
            YabauseDeInit();
            return 108;
         }
         if (ISOCD.ReadTOC(toc) <= 0 ||
             (toc[0] & 0xFFFFFFU) != 150U ||
             (toc[1] & 0xFFFFFFU) != 302U)
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 109;
         }
         FILE *gate = fopen(gate_path, "wb");
         if (!gate || fputs("1\n", gate) < 0 || fclose(gate) != 0)
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 110;
         }
         /* Two hand-authored data sectors followed by a 150-frame
            in-file pregap and two hand-authored AUDIO sectors. */
         if (!ISOCD.ReadSectorFAD(150, sector) ||
             sector[0] != 17 || sector[1] != 18 ||
             !ISOCD.ReadSectorFAD(151, sector) ||
             sector[0] != 50 || sector[1] != 51 ||
             !ISOCD.ReadSectorFAD(302, sector) ||
             sector[0] != 77 || sector[1] != 78 ||
             !ISOCD.ReadSectorFAD(303, sector) ||
             sector[0] != 88 || sector[1] != 89)
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 111;
         }
         /* Legacy callback returns success even on raw EOF read.
            Primary fread gating must suppress FAD 304. */
         ISOCD.ReadSectorFAD(304, sector);
         if (remove(gate_path) != 0)
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 112;
         }
         ISOCD.DeInit();
         YabauseDeInit();
         puts("STAGE89_REAL_YABAUSE_SPLIT_CUE_AUDIO_PASS");
         return 0;
      }
'''


def instrument_split_runner(raw: bytes) -> bytes:
    text = stage88_runner(raw).decode("utf-8")
    if (text.count(STAGE88_CONDITION) != 1 or
            text.count(CUE_CHECK) != 1 or
            MODE in text or RECEIPT in text or
            STAGE89_CONDITION == STAGE88_CONDITION):
        raise ValueError("unexpected original runner source/Stage88 layout")
    text = text.replace(STAGE88_CONDITION, STAGE89_CONDITION)
    text = text.replace(CUE_CHECK, SPLIT_CHECK + "\n" + CUE_CHECK)
    if text.count(RECEIPT) != 1 or
            text.count("ISOCD.Init(argv[2])") != 2:
        raise ValueError("invalid split runner test insertion")
    return text.encode("utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        if (a.source.resolve() == a.output.resolve() or
                a.output.exists() or a.source.name != "yui.cpp" or
                a.output.suffix != ".cpp"):
            raise ValueError("bad source or destination")
        result = instrument_split_runner(a.source.read_bytes())
        with a.output.open("xb") as out:
            out.write(result)
    except (ValueError, OSError, TypeError, UnicodeError):
        print("STAGE89_PINNED_SPLIT_CUE_RUNNER_REJECTED", file=sys.stderr)
        return 1
    print("STAGE89_PINNED_SPLIT_CUE_RUNNER_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
