#!/usr/bin/env python3
"""Stage98: pinned actual Yabause ISOCD, read-only probe of two-file CUE.

This instrumenter only accepts the exact historical public runner Git blob
through existing Stage82–89 transformations. The resulting mode never boots
the original game or prints a sector, BIOS, image or asset.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_two_track_runner import (
    STAGE89_CONDITION, SPLIT_CHECK, instrument_split_runner,
)

MODE = "vh-private-disc-probe"
PASS = "STAGE98_REAL_YABAUSE_ORIGINAL_CUE_ISO_BACKEND_PROBE_PASS"
STAGE98_CONDITION = STAGE89_CONDITION.replace(
    'strcmp(argv[1], "vh-two-file-cue-read") == 0)))',
    'strcmp(argv[1], "vh-two-file-cue-read") == 0 || '
    'strcmp(argv[1], "vh-private-disc-probe") == 0)))',
)
PROBE_CHECK = r'''      if (strcmp(argv[1], "vh-private-disc-probe") == 0)
      {
         const char *gate_path = getenv("VH_SATURN_CAPTURE_GATE");
         const char *log_path = getenv("VH_SATURN_FAD_LOG");
         unsigned char sector[2448] = {0};
         u32 toc[102] = {0};
         u32 audio_start = 0;
         if (argc != 3 || !gate_path || !gate_path[0] ||
             !log_path || !log_path[0])
         {
            YabauseDeInit();
            return 120;
         }
         if (ISOCD.Init(argv[2]) != 0)
         {
            YabauseDeInit();
            return 121;
         }
         if (ISOCD.ReadTOC(toc) <= 0 ||
             (toc[0] & 0xFFFFFFU) != 150U ||
             (audio_start = (toc[1] & 0xFFFFFFU)) < 302U)
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 122;
         }
         FILE *gate = fopen(gate_path, "wb");
         if (!gate || fputs("1\n", gate) < 0 || fclose(gate) != 0)
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 123;
         }
         /* Actual original core callback, not Python/raw-file fseek:
            FAD 150 = Sega Saturn boot sector, 151 next data sector.
            No sector bytes or game imagery are exported or printed. */
         if (!ISOCD.ReadSectorFAD(150, sector) ||
             memcmp(sector + 16, "SEGA SEGASATURN", 15) != 0 ||
             !ISOCD.ReadSectorFAD(151, sector))
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 124;
         }
         /* A sufficiently long real ISO has PVD at LBA16 => FAD166.
            The public synthetic fixture has only two data sectors. */
         if (audio_start > 317U)
         {
            if (!ISOCD.ReadSectorFAD(166, sector) ||
                sector[16] != 1 || memcmp(sector + 17, "CD001", 5) != 0)
            {
               ISOCD.DeInit();
               YabauseDeInit();
               return 125;
            }
         }
         /* From previously recorded Stage02 ISO metadata; these are
            candidate file extents, not observed game/loader activity. */
         if (audio_start > 2630U && !ISOCD.ReadSectorFAD(2479, sector))
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 126;
         }
         if (audio_start > 76637U && !ISOCD.ReadSectorFAD(76486, sector))
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 127;
         }
         /* The genuine ISOCD backend must switch FILE pointers to Track2.
            Reading a CDDA sector is not proving audio playback. */
         if (!ISOCD.ReadSectorFAD(audio_start, sector) ||
             remove(gate_path) != 0)
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 128;
         }
         ISOCD.DeInit();
         YabauseDeInit();
         puts("STAGE98_REAL_YABAUSE_ORIGINAL_CUE_ISO_BACKEND_PROBE_PASS");
         return 0;
      }
'''


def instrument_probe_runner(original: bytes) -> bytes:
    code = instrument_split_runner(original).decode("utf-8")
    if (code.count(STAGE89_CONDITION) != 1 or
            code.count(SPLIT_CHECK) != 1 or
            MODE in code or PASS in code or
            STAGE98_CONDITION == STAGE89_CONDITION):
        raise ValueError("pinned Stage89 runner layout differs")
    code = code.replace(STAGE89_CONDITION, STAGE98_CONDITION)
    code = code.replace(SPLIT_CHECK, PROBE_CHECK + "\n" + SPLIT_CHECK)
    if (code.count(PASS) != 1 or
            code.count("ISOCD.Init(argv[2])") != 3 or
            code.count('strcmp(argv[1], "vh-private-disc-probe")') != 2):
        raise ValueError("Stage98 instrumented runner not uniquely selected")
    return code.encode("utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    try:
        if (a.source.resolve() == a.output.resolve() or
                a.output.exists() or a.source.name != "yui.cpp" or
                a.output.suffix != ".cpp"):
            raise ValueError("unexpected runner input/output")
        data = instrument_probe_runner(a.source.read_bytes())
        with a.output.open("xb") as f:
            f.write(data)
    except (ValueError, OSError, TypeError, UnicodeError):
        print("STAGE98_PINNED_ISO_PROBE_INSTRUMENTATION_REJECTED", file=sys.stderr)
        return 1
    print("STAGE98_REAL_PUBLIC_YABAUSE_DISC_PROBE_BUILT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
