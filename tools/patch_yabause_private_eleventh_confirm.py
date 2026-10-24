#!/usr/bin/env python3
"""Stage144: add a guarded optional eleventh C after the tenth-C scene advance."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_tenth_confirm import (
    SETUP_CONFIRM10, CONFIRM10_PRESS, CONFIRM10_RELEASE,
)
from tools.patch_yabause_private_durable_pad_receipts import (
    instrument_full_private_durable_pad_receipts,
)

SETUP_CONFIRM11 = r'''         /* Stage144: isolate the eleventh C after the shared tenth C. */
         const char *vh126_at11 = getenv("VH_SATURN_CONFIRM_AT_FRAME11");
         const char *vh126_enable11 = getenv("VH_SATURN_CONFIRM11_ENABLED");
         int vh126_confirm_at11 = -1;
         int vh126_confirm11_enabled = -1;
         if (vh126_at11 == NULL || vh126_enable11 == NULL ||
             !*vh126_at11 || !*vh126_enable11 ||
             vh125_confirm_at10 < 0 || vh125_confirm10_enabled != 1)
            return 387;
         char *endptr126 = NULL;
         long n126 = strtol(vh126_at11, &endptr126, 10);
         if (endptr126 == vh126_at11 || *endptr126 != '\0' ||
             n126 < (long)vh125_confirm_at10 + 12L ||
             n126 > (long)frames - 8L)
            return 388;
         if (vh126_enable11[1] != '\0' ||
             (vh126_enable11[0] != '0' && vh126_enable11[0] != '1'))
            return 389;
         vh126_confirm_at11 = (int)n126;
         vh126_confirm11_enabled = (vh126_enable11[0] == '1') ? 1 : 0;
'''

CONFIRM11_PRESS = r'''            if (vh126_confirm_at11 >= 0 && frame == vh126_confirm_at11)
            {
               if (vh126_confirm11_enabled)
               {
                  const unsigned char vh126_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh126_mask) == 0U)
                     return 390;
                  PerPadCPressed(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh126_mask) != 0U)
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

CONFIRM11_RELEASE = r'''            if (vh126_confirm_at11 >= 0 && frame == vh126_confirm_at11 + 6)
            {
               if (vh126_confirm11_enabled)
               {
                  const unsigned char vh126_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh126_mask) != 0U)
                     return 394;
                  PerPadCReleased(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh126_mask) == 0U)
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

MARKER = "VH_SATURN_CONFIRM_AT_FRAME11"


def instrument_private_eleventh_confirm_on_stage143(patched: bytes) -> bytes:
    source = patched.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage143 private-frame branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if MARKER in mode or "vh126_confirm_at11" in mode:
        raise ValueError("Stage144 eleventh confirm already instrumented")
    if "VH_STAGE143_DURABLE_PAD_RECEIPTS" not in mode:
        raise ValueError("Stage144 requires Stage143 unbuffered PAD receipt patch")
    if mode.count("frames > 120000") != 1 or mode.count("YabauseEmulate()") != 1:
        raise ValueError("Stage144 requires the exact Stage143 120000-frame cap")
    if (mode.count(SETUP_CONFIRM10) != 1 or mode.count(CONFIRM10_PRESS) != 1 or
            mode.count(CONFIRM10_RELEASE) != 1 or mode.count(EMULATE_START) != 1):
        raise ValueError("Stage143 tenth-C source anchors differ")
    if mode.count("setvbuf(vh107_pad_log, NULL, _IONBF, 0)") != 1 or mode.count("setvbuf(vh109_state_log, NULL, _IONBF, 0)") != 1:
        raise ValueError("Stage144 requires exactly two Stage143 unbuffered PAD streams")
    before = {
        "press": mode.count("PerPadCPressed(vh107_pad);"),
        "release": mode.count("PerPadCReleased(vh107_pad);"),
        "event_press": mode.count("VH_PAD frame=%d button=%c action=PRESS"),
        "event_release": mode.count("VH_PAD frame=%d button=%c action=RELEASE"),
        "state_down": mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=0"),
        "state_up": mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=1"),
    }
    if before != {"press":10,"release":10,"event_press":10,"event_release":10,"state_down":10,"state_up":10}:
        raise ValueError("Stage143 tenth-C input event counts differ")
    mode = mode.replace("frames > 120000", "frames > 132000", 1)
    mode = mode.replace(SETUP_CONFIRM10, SETUP_CONFIRM10 + SETUP_CONFIRM11, 1)
    mode = mode.replace(EMULATE_START, CONFIRM11_PRESS + CONFIRM11_RELEASE + EMULATE_START, 1)
    after = {
        "press": mode.count("PerPadCPressed(vh107_pad);"),
        "release": mode.count("PerPadCReleased(vh107_pad);"),
        "event_press": mode.count("VH_PAD frame=%d button=%c action=PRESS"),
        "event_release": mode.count("VH_PAD frame=%d button=%c action=RELEASE"),
        "state_down": mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=0"),
        "state_up": mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=1"),
    }
    if after != {"press":11,"release":11,"event_press":11,"event_release":11,"state_down":11,"state_up":11}:
        raise ValueError("Stage144 eleventh-C input event counts differ")
    if mode.count(MARKER) != 1 or mode.count("frames > 132000") != 1 or "frames > 120000" in mode:
        raise ValueError("Stage144 eleventh-C cap/setup incomplete")
    if not (mode.index(SETUP_CONFIRM10) < mode.index(SETUP_CONFIRM11) < mode.index("YabauseEmulate()")):
        raise ValueError("Stage144 setup order invalid")
    if not (mode.index(CONFIRM10_PRESS) < mode.index(CONFIRM11_PRESS) < mode.index("YabauseEmulate()")):
        raise ValueError("Stage144 input order invalid")
    result = source[:start] + mode + source[end:]
    if result[:start] != source[:start] or result[len(result)-(len(source)-end):] != source[end:]:
        raise ValueError("Stage144 modified source outside the private frame branch")
    return result.encode("utf-8")


def instrument_full_private_eleventh_confirm(raw: bytes) -> bytes:
    stage143 = instrument_full_private_durable_pad_receipts(raw)
    stage144 = instrument_private_eleventh_confirm_on_stage143(stage143)
    text = stage144.decode("utf-8")
    required = (
        "VH_SATURN_CONFIRM_AT_FRAME10", "VH_SATURN_CONFIRM10_ENABLED",
        "VH_SATURN_CONFIRM_AT_FRAME11", "VH_SATURN_CONFIRM11_ENABLED",
        "frames > 132000", "VH_STAGE143_DURABLE_PAD_RECEIPTS",
        "setvbuf(vh107_pad_log, NULL, _IONBF, 0)",
        "setvbuf(vh109_state_log, NULL, _IONBF, 0)",
        "vh101_snapshot(", "vh102_snapshot(",
    )
    for token in required:
        if token not in text:
            raise ValueError("incomplete composed Stage144 runner: " + token)
    if text.count("frames > 132000") != 1:
        raise ValueError("Stage144 must have exactly one 132000-frame cap")
    return stage144


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if (args.source.name != "yui.cpp" or args.output.suffix != ".cpp" or
                args.output.exists() or args.source.resolve() == args.output.resolve()):
            raise ValueError("unsafe pinned source paths")
        output = instrument_full_private_eleventh_confirm(args.source.read_bytes())
        with args.output.open("xb") as stream:
            stream.write(output)
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE144_ELEVENTH_CONFIRM_PATCH_REJECTED", type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print("STAGE144_ELEVENTH_CONFIRM_PATCH_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
