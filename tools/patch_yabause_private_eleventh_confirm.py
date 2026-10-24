#!/usr/bin/env python3
"""Stage144: add a guarded eleventh C and extend the pinned private runner to 144k frames."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_tenth_confirm import (
    SETUP_CONFIRM10, CONFIRM10_RELEASE,
)
from tools.patch_yabause_private_durable_pad_receipts import (
    instrument_full_private_durable_pad_receipts,
)

SETUP_CONFIRM11 = r'''         /* Stage144: both cohorts share ten C presses; the eleventh is the intervention. */
         const char *vh144_at11 = getenv("VH_SATURN_CONFIRM_AT_FRAME11");
         const char *vh144_enable11 = getenv("VH_SATURN_CONFIRM11_ENABLED");
         int vh144_confirm_at11 = -1;
         int vh144_confirm11_enabled = -1;
         if (vh144_at11 == NULL || vh144_enable11 == NULL ||
             !*vh144_at11 || !*vh144_enable11 ||
             vh125_confirm_at10 < 0 || vh125_confirm10_enabled != 1)
            return 387;
         char *endptr144 = NULL;
         long n144 = strtol(vh144_at11, &endptr144, 10);
         if (endptr144 == vh144_at11 || *endptr144 != '\0' ||
             n144 < (long)vh125_confirm_at10 + 12L ||
             n144 > (long)frames - 8L)
            return 388;
         if (vh144_enable11[1] != '\0' ||
             (vh144_enable11[0] != '0' && vh144_enable11[0] != '1'))
            return 389;
         vh144_confirm_at11 = (int)n144;
         vh144_confirm11_enabled = (vh144_enable11[0] == '1') ? 1 : 0;
'''

CONFIRM11_PRESS = r'''            if (vh144_confirm_at11 >= 0 && frame == vh144_confirm_at11)
            {
               if (vh144_confirm11_enabled)
               {
                  const unsigned char vh144_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh144_mask) == 0U)
                     return 390;
                  PerPadCPressed(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh144_mask) != 0U)
                     return 391;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=PRESS\n",
                      frame, 'C') <= 0)
                     return 392;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=0\n",
                      frame, 'C') <= 0)
                     return 393;
               }
            }
'''

CONFIRM11_RELEASE = r'''            if (vh144_confirm_at11 >= 0 && frame == vh144_confirm_at11 + 6)
            {
               if (vh144_confirm11_enabled)
               {
                  const unsigned char vh144_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh144_mask) != 0U)
                     return 394;
                  PerPadCReleased(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh144_mask) == 0U)
                     return 395;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=RELEASE\n",
                      frame, 'C') <= 0)
                     return 396;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=1\n",
                      frame, 'C') <= 0)
                     return 397;
               }
            }
'''


def instrument_eleventh_confirm_on_stage143(patched: bytes) -> bytes:
    source = patched.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage143 private-frame branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if "VH_SATURN_CONFIRM_AT_FRAME11" in mode or "vh144_confirm_at11" in mode:
        raise ValueError("Stage144 eleventh confirm already instrumented")
    if mode.count("frames > 120000") != 1 or mode.count("YabauseEmulate()") != 1:
        raise ValueError("Stage144 requires the exact Stage143 120,000-frame cap")
    if mode.count(SETUP_CONFIRM10) != 1 or mode.count(CONFIRM10_RELEASE + EMULATE_START) != 1:
        raise ValueError("Stage143 tenth-confirm source anchors differ")
    if (mode.count("VH_STAGE143_DURABLE_PAD_RECEIPTS") != 2
            or mode.count("setvbuf(vh107_pad_log, NULL, _IONBF, 0)") != 1
            or mode.count("setvbuf(vh109_state_log, NULL, _IONBF, 0)") != 1):
        raise ValueError("Stage144 requires the durable Stage143 PAD streams")
    before = (
        mode.count("PerPadCPressed(vh107_pad);"),
        mode.count("PerPadCReleased(vh107_pad);"),
        mode.count("VH_PAD frame=%d button=%c action=PRESS"),
        mode.count("VH_PAD frame=%d button=%c action=RELEASE"),
        mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=0"),
        mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=1"),
    )
    if before != (10, 10, 10, 10, 10, 10):
        raise ValueError("Stage143 ten-C receipt contract differs")
    mode = mode.replace(SETUP_CONFIRM10, SETUP_CONFIRM10 + SETUP_CONFIRM11, 1)
    mode = mode.replace("frames > 120000", "frames > 144000", 1)
    mode = mode.replace(
        CONFIRM10_RELEASE + EMULATE_START,
        CONFIRM10_RELEASE + CONFIRM11_PRESS + CONFIRM11_RELEASE + EMULATE_START,
        1,
    )
    after = (
        mode.count("PerPadCPressed(vh107_pad);"),
        mode.count("PerPadCReleased(vh107_pad);"),
        mode.count("VH_PAD frame=%d button=%c action=PRESS"),
        mode.count("VH_PAD frame=%d button=%c action=RELEASE"),
        mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=0"),
        mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=1"),
    )
    if after != (11, 11, 11, 11, 11, 11):
        raise ValueError("Stage144 eleventh-C receipt insertion incomplete")
    if (mode.count("frames > 144000") != 1 or "frames > 120000" in mode
            or mode.count("VH_SATURN_CONFIRM_AT_FRAME11") != 1
            or mode.count("VH_SATURN_CONFIRM11_ENABLED") != 1
            or mode.count("frame == vh144_confirm_at11 + 6") != 1):
        raise ValueError("Stage144 frame bound or eleventh-C setup invalid")
    result = source[:start] + mode + source[end:]
    if result[:start] != source[:start] or result[len(result) - (len(source) - end):] != source[end:]:
        raise ValueError("Stage144 modified source outside the private frame branch")
    return result.encode("utf-8")


def instrument_full_private_eleventh_confirm(raw: bytes) -> bytes:
    stage143 = instrument_full_private_durable_pad_receipts(raw)
    stage144 = instrument_eleventh_confirm_on_stage143(stage143)
    text = stage144.decode("utf-8")
    required = (
        "VH_SATURN_CONFIRM_AT_FRAME10", "VH_SATURN_CONFIRM10_ENABLED",
        "VH_SATURN_CONFIRM_AT_FRAME11", "VH_SATURN_CONFIRM11_ENABLED",
        "VH_STAGE143_DURABLE_PAD_RECEIPTS", "frames > 144000",
        "vh101_snapshot(", "vh102_snapshot(",
    )
    for token in required:
        if token not in text:
            raise ValueError("incomplete Stage144 composed runner: " + token)
    if (text.count("PerPadCPressed(vh107_pad);") != 11
            or text.count("PerPadCReleased(vh107_pad);") != 11
            or text.count("setvbuf(vh107_pad_log, NULL, _IONBF, 0)") != 1
            or text.count("setvbuf(vh109_state_log, NULL, _IONBF, 0)") != 1):
        raise ValueError("Stage144 input and durable receipt count mismatch")
    return stage144


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if (args.source.name != "yui.cpp" or args.output.suffix != ".cpp"
                or args.output.exists() or args.source.resolve() == args.output.resolve()):
            raise ValueError("unsafe pinned source paths")
        result = instrument_full_private_eleventh_confirm(args.source.read_bytes())
        with args.output.open("xb") as stream:
            stream.write(result)
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE144_ELEVENTH_CONFIRM_PATCH_REJECTED", type(exc).__name__, str(exc),
              file=sys.stderr)
        return 1
    print("STAGE144_ELEVENTH_CONFIRM_RUNNER_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
