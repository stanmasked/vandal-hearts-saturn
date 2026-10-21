#!/usr/bin/env python3
"""Stage76: opt-in, exact-anchor diagnostic hook for local Yabause ISO CD reads.

This source transformation does not read or copy any Saturn disc content.
It inserts a disabled-by-default numeric-only FAD event logger into the
ISOCDReadSectorFAD callback of a locally held Yabause cdbase.c checkout.
The full third-party emulator and original game are not run by this tool.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

FUNCTION = "static int ISOCDReadSectorFAD(u32 FAD, void *buffer) {"
FOLLOWING = "static void ISOCDReadAheadFAD"
FLAG = "VH_SATURN_FAD_LOG"
RETURN_PATTERN = re.compile(r"(?m)^[ \t]*return 1;[ \t]*\r?\n[ \t]*\}")

HOOK = r'''   /* VH Stage76: opt-in numeric sector-read diagnostic. */
   if (num_read > 0) {
      const char *vh_trace_path = getenv("VH_SATURN_FAD_LOG");
      if (vh_trace_path && vh_trace_path[0] != '\0') {
         FILE *vh_trace = fopen(vh_trace_path, "a");
         if (vh_trace) {
            fprintf(vh_trace, "VHCD_FAD %u\n", (unsigned int)FAD);
            fclose(vh_trace);
         }
      }
   }
'''


def patch_cdbase(source: str) -> str:
    if not isinstance(source, str):
        raise ValueError("expected C source text")
    if FLAG in source:
        raise ValueError("already instrumented or conflicting Yabause source")
    if source.count(FUNCTION) != 1:
        raise ValueError("exact Yabause ISOCDReadSectorFAD function not found")
    start = source.index(FUNCTION)
    end = source.find(FOLLOWING, start + len(FUNCTION))
    if end == -1:
        raise ValueError("unable to bound Yabause CD read function")
    body = source[start:end]
    if "num_read" not in body or "fread(" not in body:
        raise ValueError("Yabause callback layout changed")
    matches = list(RETURN_PATTERN.finditer(body))
    if len(matches) != 1:
        raise ValueError("unexpected Yabause return layout")
    insert_at = start + matches[0].start()
    newline = "\r\n" if "\r\n" in source else "\n"
    return source[:insert_at] + HOOK.replace("\n", newline) + source[insert_at:]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.source.resolve() == args.output.resolve() or args.output.exists():
            raise ValueError("refusing in-place patch or output overwrite")
        raw = args.source.read_bytes()
        patched = patch_cdbase(raw.decode("utf-8"))
        args.output.write_bytes(patched.encode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print("YABAUSE_CD_HOOK_REJECTED " + type(exc).__name__, file=sys.stderr)
        return 1
    print("YABAUSE_ISO_FAD_HOOK_PREPARED independent_emulator_build_verified=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
