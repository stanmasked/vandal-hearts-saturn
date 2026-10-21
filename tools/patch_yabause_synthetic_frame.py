#!/usr/bin/env python3
"""Stage83: pinned real Yabause runner, one frame of invented SH-2 instructions.

This test uses a three-instruction program created entirely in the test
fixture: ADD #1,R0; BRA -3; NOP (branch delay slot).
Never accesses Saturn game images, BIOS files, screenshots, or CD sectors.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.patch_yabause_no_media_runner import instrument_runner, SUCCESS

MODE = "vh-synthetic-sh2-frame"
RECEIPT = "STAGE83_REAL_YABAUSE_SYNTHETIC_SH2_FRAME_PASS"

STAGE82_CONDITION = 'if (argc == 2 && strcmp(argv[1], "vh-no-media-init") == 0)'
STAGE83_CONDITION = (
    'if (argc == 2 && (strcmp(argv[1], "vh-no-media-init") == 0 || '
    'strcmp(argv[1], "vh-synthetic-sh2-frame") == 0))'
)
TAIL = '      YabauseDeInit();\n      puts("' + SUCCESS + '");\n      return 0;'

FRAME_CHECK = r'''      if (strcmp(argv[1], "vh-synthetic-sh2-frame") == 0)
      {
         /* Three invented instructions in Saturn high work RAM:
            7001 = ADD #1,R0; AFFD = BRA back to ADD; 0009 = NOP. */
         const u32 synthetic_pc = 0x06000000U;
         sh2regs_struct before = { 0 };
         sh2regs_struct after = { 0 };
         if (!MSH2 || !MSH2->MappedMemoryWriteWord ||
             !MSH2->MappedMemoryReadWord)
         {
            fputs("STAGE83_SYNTHETIC_SH2_MEMORY_UNAVAILABLE\n", stderr);
            YabauseDeInit();
            return 83;
         }
         MSH2->MappedMemoryWriteWord(MSH2, synthetic_pc, 0x7001);
         MSH2->MappedMemoryWriteWord(MSH2, synthetic_pc + 2, 0xAFFD);
         MSH2->MappedMemoryWriteWord(MSH2, synthetic_pc + 4, 0x0009);
         if (MSH2->MappedMemoryReadWord(MSH2, synthetic_pc) != 0x7001 ||
             MSH2->MappedMemoryReadWord(MSH2, synthetic_pc + 2) != 0xAFFD ||
             MSH2->MappedMemoryReadWord(MSH2, synthetic_pc + 4) != 0x0009)
         {
            fputs("STAGE83_SYNTHETIC_SH2_PROGRAM_WRITE_FAIL\n", stderr);
            YabauseDeInit();
            return 84;
         }
         SH2GetRegisters(MSH2, &before);
         before.PC = synthetic_pc;
         before.R[0] = 0;
         before.SR.part.I = 15;  /* mask IRQs for invented tight loop */
         SH2SetRegisters(MSH2, &before);
         if (YabauseEmulate() != 0)
         {
            fputs("STAGE83_SYNTHETIC_FRAME_EXECUTION_FAIL\n", stderr);
            YabauseDeInit();
            return 85;
         }
         SH2GetRegisters(MSH2, &after);
         if (after.R[0] == 0 || after.PC < synthetic_pc ||
             after.PC > synthetic_pc + 4)
         {
            fputs("STAGE83_SYNTHETIC_REGISTER_EVIDENCE_FAIL\n", stderr);
            YabauseDeInit();
            return 86;
         }
         YabauseDeInit();
         puts("STAGE83_REAL_YABAUSE_SYNTHETIC_SH2_FRAME_PASS");
         return 0;
      }
'''

def instrument_frame_runner(original: bytes) -> bytes:
    # Stage82 already requires the immutable original upstream runner Git blob.
    patched = instrument_runner(original).decode("utf-8")
    if patched.count(STAGE82_CONDITION) != 1 or patched.count(TAIL) != 1:
        raise ValueError("unexpected pinned Stage82 runner layout")
    if MODE in patched or RECEIPT in patched:
        raise ValueError("already instrumented")
    patched = patched.replace(STAGE82_CONDITION, STAGE83_CONDITION)
    patched = patched.replace(TAIL, FRAME_CHECK + "\n" + TAIL)
    if patched.count("YabauseEmulate()") != 1 or patched.count(RECEIPT) != 1:
        raise ValueError("unexpected Stage83 frame instrumentation")
    return patched.encode("utf-8")


def patch_runner_file(source: Path, output: Path) -> dict:
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError("refusing overwrite")
    if source.name != "yui.cpp" or output.suffix != ".cpp":
        raise ValueError("invalid runner input/output name")
    patched = instrument_frame_runner(source.read_bytes())
    with output.open("xb") as stream:
        stream.write(patched)
    return {
        "public_yabause_runner_verified": True,
        "synthetic_sh2_instructions_only": True,
        "original_game_media_present": False,
        "bios_file_present": False,
        "initialization_executed": False,
        "sh2_frame_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(patch_runner_file(args.source, args.output), sort_keys=True))
        return 0
    except (TypeError, ValueError, OSError, UnicodeError):
        print("STAGE83_PINNED_RUNNER_PATCH_REJECTED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
