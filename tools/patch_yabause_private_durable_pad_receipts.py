#!/usr/bin/env python3
"""Stage143: make host-side PAD event/state receipts unbuffered.

Composes the pinned Stage125 tenth-C source transform, then applies one exact
Stage143 transformation. Unbuffered stdio preserves each receipt line across a
bounded SIGTERM stop; it does not claim power-loss durability or guest input
consumption. No original media is read by the transformer.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_tenth_confirm import instrument_full_private_tenth_confirm

PAD_OPEN = '''         vh107_pad_log = fopen(vh107_pad_log_path, "wx");
         if (!vh107_pad_log)
         {
            YabauseDeInit();
            return 226;
         }
'''
STATE_OPEN = '''         vh109_state_log = fopen(vh109_state_path, "wx");
         if (!vh109_state_log)
            return 232;
'''

PAD_UNBUFFERED = '''         /* VH_STAGE143_DURABLE_PAD_RECEIPTS: keep event lines unbuffered across bounded stops. */
         if (setvbuf(vh107_pad_log, NULL, _IONBF, 0) != 0)
         {
            fclose(vh107_pad_log);
            vh107_pad_log = NULL;
            YabauseDeInit();
            return 385;
         }
'''
STATE_UNBUFFERED = '''         /* VH_STAGE143_DURABLE_PAD_RECEIPTS: keep state lines unbuffered across bounded stops. */
         if (setvbuf(vh109_state_log, NULL, _IONBF, 0) != 0)
         {
            fclose(vh109_state_log);
            vh109_state_log = NULL;
            if (vh107_pad_log)
            {
               fclose(vh107_pad_log);
               vh107_pad_log = NULL;
            }
            YabauseDeInit();
            return 386;
         }
'''
MARKER = "VH_STAGE143_DURABLE_PAD_RECEIPTS"


def instrument_durable_pad_receipts_on_stage125(patched: bytes) -> bytes:
    source = patched.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage125 private-frame branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if MARKER in mode or "setvbuf(vh107_pad_log" in mode or "setvbuf(vh109_state_log" in mode:
        raise ValueError("Stage143 durable PAD receipt patch already applied")
    if mode.count(PAD_OPEN) != 1 or mode.count(STATE_OPEN) != 1:
        raise ValueError("Stage125 PAD stream open anchors differ")
    if "#include <stdio.h>" not in source:
        raise ValueError("stdio declarations unavailable for Stage143 setvbuf")
    before_pad_writes = mode.count("fprintf(vh107_pad_log,")
    before_state_writes = mode.count("fprintf(vh109_state_log,")
    before_events = (mode.count("PerPadStartPressed(vh107_pad);"),
                     mode.count("PerPadStartReleased(vh107_pad);"),
                     mode.count("PerPadCPressed(vh107_pad);"),
                     mode.count("PerPadCReleased(vh107_pad);"))
    if not before_pad_writes or not before_state_writes or before_events[2:] != (10, 10):
        raise ValueError("Stage125 PAD event count does not match ten-C experiment")
    mode = mode.replace(PAD_OPEN, PAD_OPEN + PAD_UNBUFFERED, 1)
    mode = mode.replace(STATE_OPEN, STATE_OPEN + STATE_UNBUFFERED, 1)
    if (mode.count("setvbuf(vh107_pad_log, NULL, _IONBF, 0)") != 1 or
            mode.count("setvbuf(vh109_state_log, NULL, _IONBF, 0)") != 1):
        raise ValueError("Stage143 unbuffered stream setup incomplete")
    if not (mode.index(PAD_OPEN) < mode.index("setvbuf(vh107_pad_log") < mode.index("fprintf(vh107_pad_log,")):
        raise ValueError("PAD event stream setup order invalid")
    if not (mode.index(STATE_OPEN) < mode.index("setvbuf(vh109_state_log") < mode.index("fprintf(vh109_state_log,")):
        raise ValueError("PAD state stream setup order invalid")
    if (mode.count("fprintf(vh107_pad_log,") != before_pad_writes or
            mode.count("fprintf(vh109_state_log,") != before_state_writes or
            before_events != (mode.count("PerPadStartPressed(vh107_pad);"),
                              mode.count("PerPadStartReleased(vh107_pad);"),
                              mode.count("PerPadCPressed(vh107_pad);"),
                              mode.count("PerPadCReleased(vh107_pad);"))):
        raise ValueError("Stage143 changed inherited PAD event semantics")
    result = source[:start] + mode + source[end:]
    if result[:start] != source[:start] or result[len(result)-(len(source)-end):] != source[end:]:
        raise ValueError("Stage143 modified source outside the private frame branch")
    return result.encode("utf-8")


def instrument_full_private_durable_pad_receipts(raw: bytes) -> bytes:
    stage125 = instrument_full_private_tenth_confirm(raw)
    stage143 = instrument_durable_pad_receipts_on_stage125(stage125)
    text = stage143.decode("utf-8")
    required = (
        "VH_SATURN_CONFIRM_AT_FRAME10", "VH_SATURN_CONFIRM10_ENABLED",
        "frames > 120000", "VH_STAGE143_DURABLE_PAD_RECEIPTS",
        "vh101_snapshot(", "vh102_snapshot(",
    )
    if MARKER not in text:
        raise ValueError("Stage143 durable receipt markers missing")
    for token in required:
        if token not in text:
            raise ValueError("incomplete Stage143 composed runner: " + token)
    if text.count("setvbuf(vh107_pad_log, NULL, _IONBF, 0)") != 1 or text.count("setvbuf(vh109_state_log, NULL, _IONBF, 0)") != 1:
        raise ValueError("Stage143 requires exactly two unbuffered PAD streams")
    return stage143


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if (args.source.name != "yui.cpp" or args.output.suffix != ".cpp" or
                args.output.exists() or args.source.resolve() == args.output.resolve()):
            raise ValueError("unsafe pinned source paths")
        output = instrument_full_private_durable_pad_receipts(args.source.read_bytes())
        with args.output.open("xb") as stream:
            stream.write(output)
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE143_DURABLE_PAD_PATCH_REJECTED", type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print("STAGE143_DURABLE_PAD_RECEIPTS_PATCH_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
