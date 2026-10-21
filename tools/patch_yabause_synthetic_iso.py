#!/usr/bin/env python3
"""Stage84: call the real pinned Yabause ISOCD backend on a fabricated ISO file.

Exercises the actual patched callback in a fully linked Yabause process.
The fabricated two-sector file is not a bootable Saturn game or source asset.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.patch_yabause_synthetic_frame import (
    FRAME_CHECK, STAGE83_CONDITION, instrument_frame_runner,
)

MODE = "vh-synthetic-iso-read"
RECEIPT = "STAGE84_REAL_YABAUSE_SYNTHETIC_ISO_CD_PASS"
NEW_CONDITION = STAGE83_CONDITION.replace(
    'strcmp(argv[1], "vh-synthetic-sh2-frame") == 0))',
    'strcmp(argv[1], "vh-synthetic-sh2-frame") == 0 || '
    'strcmp(argv[1], "vh-synthetic-iso-read") == 0))',
)

CD_CHECK = r'''      if (strcmp(argv[1], "vh-synthetic-iso-read") == 0)
      {
         const char *gate_path = getenv("VH_SATURN_CAPTURE_GATE");
         const char *log_path = getenv("VH_SATURN_FAD_LOG");
         const char *fixture_name = "vh_created_iso_fixture.iso";
         unsigned char sector[2448] = {0};
         if (!gate_path || !gate_path[0] || !log_path || !log_path[0])
         {
            fputs("STAGE84_SYNTHETIC_CD_ENV_MISSING\n", stderr);
            YabauseDeInit();
            return 87;
         }
         FILE *fixture = fopen(fixture_name, "wb");
         if (!fixture)
         {
            YabauseDeInit();
            return 88;
         }
         /* Exactly two invented 2048-byte sectors: no ISO9660 filesystem,
            Saturn boot header, game resource or copyrighted disc material. */
         for (int n = 0; n < 4096; ++n)
         {
            unsigned char b = (unsigned char)(((n / 2048) * 33 + n * 11 + 7) & 255);
            if (fputc(b, fixture) == EOF)
            {
               fclose(fixture);
               YabauseDeInit();
               return 89;
            }
         }
         if (fclose(fixture))
         {
            YabauseDeInit();
            return 90;
         }
         if (ISOCD.Init(fixture_name) != 0)
         {
            YabauseDeInit();
            return 91;
         }
         /* Closed gate: a successful real ISO read cannot log. */
         if (!ISOCD.ReadSectorFAD(150, sector) || sector[16] != 7)
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 92;
         }
         FILE *gate = fopen(gate_path, "wb");
         if (!gate || fputs("1\n", gate) < 0 || fclose(gate))
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 93;
         }
         /* Open gate: real raw-data reads at fabricated FAD 150 and 151. */
         if (!ISOCD.ReadSectorFAD(150, sector) || sector[16] != 7 ||
             !ISOCD.ReadSectorFAD(151, sector) || sector[16] != 40)
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 94;
         }
         /* Historical Yabause returns 1 past EOF even when fread fails;
            our instrumentation must not record this attempted FAD 152. */
         if (!ISOCD.ReadSectorFAD(152, sector))
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 95;
         }
         gate = fopen(gate_path, "wb");
         if (!gate || fputs("1\r\n", gate) < 0 || fclose(gate))
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 96;
         }
         if (!ISOCD.ReadSectorFAD(150, sector) ||
             remove(gate_path) != 0 ||
             !ISOCD.ReadSectorFAD(151, sector))
         {
            ISOCD.DeInit();
            YabauseDeInit();
            return 97;
         }
         ISOCD.DeInit();
         YabauseDeInit();
         puts("STAGE84_REAL_YABAUSE_SYNTHETIC_ISO_CD_PASS");
         return 0;
      }
'''

def instrument_cd_runner(original: bytes) -> bytes:
    # First check the exact original public pinned runner Git blob and then
    # construct Stage82 and Stage83 modes from verified transformation code.
    patched = instrument_frame_runner(original).decode("utf-8")
    if patched.count(STAGE83_CONDITION) != 1 or patched.count(FRAME_CHECK) != 1:
        raise ValueError("unexpected original/Stage83 runner structure")
    if MODE in patched or RECEIPT in patched:
        raise ValueError("repeated instrumentation")
    if NEW_CONDITION == STAGE83_CONDITION:
        raise ValueError("failed to extend selection")
    patched = patched.replace(STAGE83_CONDITION, NEW_CONDITION)
    patched = patched.replace(FRAME_CHECK, CD_CHECK + "\n" + FRAME_CHECK)
    if patched.count("ISOCD.ReadSectorFAD(") != 6 or patched.count(RECEIPT) != 1:
        raise ValueError("unexpected real ISO callback fixture")
    return patched.encode("utf-8")


def patch_runner_file(source: Path, output: Path) -> dict:
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError("refusing overwrite")
    if source.name != "yui.cpp" or output.suffix != ".cpp":
        raise ValueError("invalid upstream runner file name")
    # Verify immutable upstream contents and the exact callback layout before
    # creating any output, including on a rejected input.
    patched = instrument_cd_runner(source.read_bytes())
    with output.open("xb") as stream:
        stream.write(patched)
    return {
        "verified_pinned_public_runner": True,
        "synthetic_iso_sectors": 2,
        "original_game_media_used": False,
        "real_cd_read_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(patch_runner_file(args.source, args.output), sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, UnicodeError):
        print("STAGE84_PINNED_YABAUSE_ISO_PATCH_REJECTED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
