#!/usr/bin/env python3
"""Stage88: exact-blob original Yabause runner with an invented CUE open mode.

The opt-in mode reads only tiny fabricated 2352-byte sectors. The private
wrapper and public ISO CD backend are real, but no original game is used.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from tools.patch_yabause_synthetic_iso import (
    NEW_CONDITION as STAGE84_CONDITION, CD_CHECK, instrument_cd_runner,
)

MODE = "vh-exact-cue-read"
RECEIPT = "STAGE88_REAL_YABAUSE_SYNTHETIC_CUE_OPEN_PASS"
STAGE88_CONDITION = STAGE84_CONDITION.replace(
    'strcmp(argv[1], "vh-synthetic-iso-read") == 0))',
    'strcmp(argv[1], "vh-synthetic-iso-read") == 0 || '
    'strcmp(argv[1], "vh-exact-cue-read") == 0))',
)
CUE_CHECK = r'''      if (strcmp(argv[1], "vh-exact-cue-read") == 0)
      {
         const char *gate_path = getenv("VH_SATURN_CAPTURE_GATE");
         const char *log_path = getenv("VH_SATURN_FAD_LOG");
         unsigned char buffer[2448] = {0};
         if (argc != 3 || !gate_path || !gate_path[0] ||
             !log_path || !log_path[0])
         {
            YabauseDeInit();
            return 100;
         }
         /* The exact argv[2] path must pass to the genuine ISOCD backend.
            No file content is generated, copied or dumped by this mode. */
         if (ISOCD.Init(argv[2]) != 0)
         {
            YabauseDeInit();
            return 101;
         }
         FILE *gate = fopen(gate_path, "wb");
         if (!gate)
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 102;
         }
         if (fputs("1\n", gate) < 0 || fclose(gate) != 0)
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 103;
         }
         /* Real MODE1/2352 sectors from the invented two-sector BIN. */
         if (!ISOCD.ReadSectorFAD(150, buffer) ||
             buffer[0] != 17 || buffer[1] != 18 ||
             !ISOCD.ReadSectorFAD(151, buffer) ||
             buffer[0] != 50 || buffer[1] != 51)
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 104;
         }
         /* The upstream callback returns 1 even when the primary fread
            reaches EOF. Stage79 logging must suppress this FAD. */
         if (!ISOCD.ReadSectorFAD(152, buffer))
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 105;
         }
         if (remove(gate_path) != 0)
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 106;
         }
         ISOCD.DeInit();
         YabauseDeInit();
         puts("STAGE88_REAL_YABAUSE_SYNTHETIC_CUE_OPEN_PASS");
         return 0;
      }
'''


def instrument_runner(raw: bytes) -> bytes:
    # Existing Stage84 transformation checks original upstream SHA-1 blob.
    source = instrument_cd_runner(raw).decode("utf-8")
    if (source.count(STAGE84_CONDITION) != 1 or
            source.count(CD_CHECK) != 1 or
            STAGE88_CONDITION == STAGE84_CONDITION or
            MODE in source or RECEIPT in source):
        raise ValueError("unrecognized pinned original runner layout")
    source = source.replace(STAGE84_CONDITION, STAGE88_CONDITION)
    source = source.replace(CD_CHECK, CUE_CHECK + "\n" + CD_CHECK)
    if (source.count("ISOCD.Init(argv[2])") != 1 or
            source.count(RECEIPT) != 1 or
            source.count("VH_SATURN_FAD_LOG") < 2):
        raise ValueError("incomplete Stage88 real CUE bridge")
    return source.encode("utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    try:
        if (a.source.resolve() == a.output.resolve() or
                a.output.exists() or a.source.name != "yui.cpp" or
                a.output.suffix != ".cpp"):
            raise ValueError("refuse modified input/output layout")
        patched = instrument_runner(a.source.read_bytes())
        with a.output.open("xb") as stream:
            stream.write(patched)
    except (OSError, ValueError, UnicodeError, TypeError):
        print("STAGE88_PINNED_RUNNER_PATCH_REJECTED", file=sys.stderr)
        return 1
    print("STAGE88_PUBLIC_UPSTREAM_CUE_READER_INSTRUMENTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
