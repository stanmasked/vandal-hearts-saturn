#!/usr/bin/env python3
"""Stage77 opt-in window-gated variant of Stage76 Yabause ISO CD capture hook.

Source transformation only. Does not build or launch Yabause, open a disc,
or assert that a gate corresponds to an actual gameplay scene.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.saturn_yabause_cdbase_hook import patch_cdbase

LEGACY = r'''      if (vh_trace_path && vh_trace_path[0] != '\0') {
         FILE *vh_trace = fopen(vh_trace_path, "a");
         if (vh_trace) {
            fprintf(vh_trace, "VHCD_FAD %u\n", (unsigned int)FAD);
            fclose(vh_trace);
         }
      }'''

GATED = r'''      /* Gate must contain exactly ASCII 1 plus LF, read at callback time. */
      const char *vh_gate_path = getenv("VH_SATURN_CAPTURE_GATE");
      if (vh_trace_path && vh_trace_path[0] != '\0' &&
          vh_gate_path && vh_gate_path[0] != '\0') {
         FILE *vh_gate = fopen(vh_gate_path, "rb");
         if (vh_gate) {
            int vh_first = fgetc(vh_gate);
            int vh_second = fgetc(vh_gate);
            int vh_third = fgetc(vh_gate);
            fclose(vh_gate);
            if (vh_first == '1' && vh_second == '\n' && vh_third == EOF) {
               FILE *vh_trace = fopen(vh_trace_path, "a");
               if (vh_trace) {
                  fprintf(vh_trace, "VHCD_FAD %u\n", (unsigned int)FAD);
                  fclose(vh_trace);
               }
            }
         }
      }'''


def patch_gated_cdbase(original: str) -> str:
    first = patch_cdbase(original)
    newline = "\r\n" if "\r\n" in first else "\n"
    before = LEGACY.replace("\n", newline)
    after = GATED.replace("\n", newline)
    if first.count(before) != 1:
        raise ValueError("Stage76 CD logger layout has changed")
    return first.replace(before, after)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.source.resolve() == args.output.resolve() or args.output.exists():
            raise ValueError("refusing to overwrite source or existing file")
        raw = args.source.read_bytes()
        changed = patch_gated_cdbase(raw.decode("utf-8"))
        args.output.write_bytes(changed.encode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print("VH_GATED_YABAUSE_PATCH_REJECTED " + type(exc).__name__,
              file=sys.stderr)
        return 1
    print("VH_GATED_YABAUSE_PATCH_READY full_emulator_build_verified=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
