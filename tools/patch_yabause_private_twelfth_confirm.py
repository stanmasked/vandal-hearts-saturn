#!/usr/bin/env python3
"""Stage145: add a guarded optional twelfth C after the shared eleventh C."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_eleventh_confirm import (
    SETUP_CONFIRM11, CONFIRM11_PRESS, CONFIRM11_RELEASE,
    instrument_full_private_eleventh_confirm,
)

SETUP_CONFIRM12 = r'''         /* Stage145: isolate the twelfth C after the shared eleventh C. */
         const char *vh127_at12 = getenv("VH_SATURN_CONFIRM_AT_FRAME12");
         const char *vh127_enable12 = getenv("VH_SATURN_CONFIRM12_ENABLED");
         int vh127_confirm_at12 = -1;
         int vh127_confirm12_enabled = -1;
         if (vh127_at12 == NULL || vh127_enable12 == NULL ||
             !*vh127_at12 || !*vh127_enable12 ||
             vh126_confirm_at11 < 0 || vh126_confirm11_enabled != 1)
            return 398;
         char *endptr127 = NULL;
         long n127 = strtol(vh127_at12, &endptr127, 10);
         if (endptr127 == vh127_at12 || *endptr127 != '\0' ||
             n127 < (long)vh126_confirm_at11 + 12L ||
             n127 > (long)frames - 8L)
            return 399;
         if (vh127_enable12[1] != '\0' ||
             (vh127_enable12[0] != '0' && vh127_enable12[0] != '1'))
            return 400;
         vh127_confirm_at12 = (int)n127;
         vh127_confirm12_enabled = (vh127_enable12[0] == '1') ? 1 : 0;
'''

CONFIRM12_PRESS = r'''            if (vh127_confirm_at12 >= 0 && frame == vh127_confirm_at12)
            {
               if (vh127_confirm12_enabled)
               {
                  const unsigned char vh127_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh127_mask) == 0U)
                     return 401;
                  PerPadCPressed(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh127_mask) != 0U)
                     return 402;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=PRESS\n",
                      frame, 'C') <= 0)
                     return 403;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=0\n",
                      frame, 'C') <= 0)
                     return 404;
               }
            }
'''

CONFIRM12_RELEASE = r'''            if (vh127_confirm_at12 >= 0 && frame == vh127_confirm_at12 + 6)
            {
               if (vh127_confirm12_enabled)
               {
                  const unsigned char vh127_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh127_mask) != 0U)
                     return 405;
                  PerPadCReleased(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh127_mask) == 0U)
                     return 406;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=RELEASE\n",
                      frame, 'C') <= 0)
                     return 407;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=1\n",
                      frame, 'C') <= 0)
                     return 408;
               }
            }
'''

MARKER = "VH_SATURN_CONFIRM_AT_FRAME12"


def instrument_private_twelfth_confirm_on_stage144(patched: bytes) -> bytes:
    source = patched.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage144 private-frame branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if MARKER in mode or "vh127_confirm_at12" in mode:
        raise ValueError("Stage145 twelfth confirm already instrumented")
    if "VH_STAGE143_DURABLE_PAD_RECEIPTS" not in mode:
        raise ValueError("Stage145 requires Stage143 unbuffered PAD receipt patch")
    if mode.count("frames > 132000") != 1 or mode.count("YabauseEmulate()") != 1:
        raise ValueError("Stage145 requires the exact Stage144 132000-frame cap")
    if (mode.count(SETUP_CONFIRM11) != 1 or mode.count(CONFIRM11_PRESS) != 1 or
            mode.count(CONFIRM11_RELEASE) != 1 or mode.count(EMULATE_START) != 1):
        raise ValueError("Stage144 eleventh-C source anchors differ")
    if mode.count("setvbuf(vh107_pad_log, NULL, _IONBF, 0)") != 1 or mode.count("setvbuf(vh109_state_log, NULL, _IONBF, 0)") != 1:
        raise ValueError("Stage145 requires exactly two Stage144 unbuffered PAD streams")
    before = {
        "press": mode.count("PerPadCPressed(vh107_pad);"),
        "release": mode.count("PerPadCReleased(vh107_pad);"),
        "event_press": mode.count("VH_PAD frame=%d button=%c action=PRESS"),
        "event_release": mode.count("VH_PAD frame=%d button=%c action=RELEASE"),
        "state_down": mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=0"),
        "state_up": mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=1"),
    }
    if before != {"press": 11, "release": 11, "event_press": 11, "event_release": 11, "state_down": 11, "state_up": 11}:
        raise ValueError("Stage144 eleventh-C input event counts differ")
    mode = mode.replace("frames > 132000", "frames > 144000", 1)
    mode = mode.replace(SETUP_CONFIRM11, SETUP_CONFIRM11 + SETUP_CONFIRM12, 1)
    mode = mode.replace(EMULATE_START, CONFIRM12_PRESS + CONFIRM12_RELEASE + EMULATE_START, 1)
    after = {
        "press": mode.count("PerPadCPressed(vh107_pad);"),
        "release": mode.count("PerPadCReleased(vh107_pad);"),
        "event_press": mode.count("VH_PAD frame=%d button=%c action=PRESS"),
        "event_release": mode.count("VH_PAD frame=%d button=%c action=RELEASE"),
        "state_down": mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=0"),
        "state_up": mode.count("VH_PADSTATE frame=%d button=%c active_low_bit=1"),
    }
    if after != {"press": 12, "release": 12, "event_press": 12, "event_release": 12, "state_down": 12, "state_up": 12}:
        raise ValueError("Stage145 twelfth-C input event counts differ")
    if mode.count(MARKER) != 1 or mode.count("frames > 144000") != 1 or "frames > 132000" in mode:
        raise ValueError("Stage145 twelfth-C cap/setup incomplete")
    if not (mode.index(SETUP_CONFIRM11) < mode.index(SETUP_CONFIRM12) < mode.index("YabauseEmulate()")):
        raise ValueError("Stage145 setup order invalid")
    if not (mode.index(CONFIRM11_PRESS) < mode.index(CONFIRM12_PRESS) < mode.index("YabauseEmulate()")):
        raise ValueError("Stage145 input order invalid")
    result = source[:start] + mode + source[end:]
    if result[:start] != source[:start] or result[len(result)-(len(source)-end):] != source[end:]:
        raise ValueError("Stage145 modified source outside the private frame branch")
    return result.encode("utf-8")


def instrument_full_private_twelfth_confirm(raw: bytes) -> bytes:
    stage144 = instrument_full_private_eleventh_confirm(raw)
    stage145 = instrument_private_twelfth_confirm_on_stage144(stage144)
    text = stage145.decode("utf-8")
    required = (
        "VH_SATURN_CONFIRM_AT_FRAME10", "VH_SATURN_CONFIRM10_ENABLED",
        "VH_SATURN_CONFIRM_AT_FRAME11", "VH_SATURN_CONFIRM11_ENABLED",
        "VH_SATURN_CONFIRM_AT_FRAME12", "VH_SATURN_CONFIRM12_ENABLED",
        "frames > 144000", "VH_STAGE143_DURABLE_PAD_RECEIPTS",
        "setvbuf(vh107_pad_log, NULL, _IONBF, 0)",
        "setvbuf(vh109_state_log, NULL, _IONBF, 0)",
        "vh101_snapshot(", "vh102_snapshot(",
    )
    for token in required:
        if token not in text:
            raise ValueError("incomplete composed Stage145 runner: " + token)
    if text.count("frames > 144000") != 1:
        raise ValueError("Stage145 must have exactly one 144000-frame cap")
    return stage145


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if (args.source.name != "yui.cpp" or args.output.suffix != ".cpp" or
                args.output.exists() or args.source.resolve() == args.output.resolve()):
            raise ValueError("unsafe pinned source paths")
        output = instrument_full_private_twelfth_confirm(args.source.read_bytes())
        with args.output.open("xb") as stream:
            stream.write(output)
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE145_TWELFTH_CONFIRM_PATCH_REJECTED", type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print("STAGE145_TWELFTH_CONFIRM_PATCH_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
