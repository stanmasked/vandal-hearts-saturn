#!/usr/bin/env python3
"""Stage125: add a guarded optional tenth C after the ninth-C dialogue."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from tools.patch_yabause_native_start_bit import MODE_START, MODE_END
from tools.patch_yabause_private_start_sequence import EMULATE_START
from tools.patch_yabause_private_ninth_confirm import instrument_full_private_ninth_confirm

NINTH_SETUP_END = (
    "         vh124_confirm_at9 = (int)n124;\n"
    "         vh124_confirm9_enabled = (vh124_enable9[0] == '1') ? 1 : 0;\n"
)

SETUP_CONFIRM10 = r'''         /* Stage125: the previous nine C presses must be identical in both runs. */
         const char *vh125_at10 = getenv("VH_SATURN_CONFIRM_AT_FRAME10");
         const char *vh125_enable10 = getenv("VH_SATURN_CONFIRM10_ENABLED");
         int vh125_confirm_at10 = -1;
         int vh125_confirm10_enabled = -1;
         if (vh125_at10 == NULL || vh125_enable10 == NULL ||
             !*vh125_at10 || !*vh125_enable10 ||
             vh124_confirm_at9 < 0 || vh124_confirm9_enabled != 1)
            return 374;
         char *endptr125 = NULL;
         long n125 = strtol(vh125_at10, &endptr125, 10);
         if (endptr125 == vh125_at10 || *endptr125 != '\0' ||
             n125 < (long)vh124_confirm_at9 + 12L ||
             n125 > (long)frames - 8L)
            return 375;
         if (vh125_enable10[1] != '\0' ||
             (vh125_enable10[0] != '0' && vh125_enable10[0] != '1'))
            return 376;
         vh125_confirm_at10 = (int)n125;
         vh125_confirm10_enabled = (vh125_enable10[0] == '1') ? 1 : 0;
'''

CONFIRM10_PRESS = r'''            if (vh125_confirm_at10 >= 0 && frame == vh125_confirm_at10)
            {
               if (vh125_confirm10_enabled)
               {
                  const unsigned char vh125_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh125_mask) == 0U)
                     return 377;
                  PerPadCPressed(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh125_mask) != 0U)
                     return 378;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=PRESS\n",
                      frame, 'C') <= 0)
                     return 379;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=0\n",
                      frame, 'C') <= 0)
                     return 380;
               }
            }
'''

CONFIRM10_RELEASE = r'''            if (vh125_confirm_at10 >= 0 && frame == vh125_confirm_at10 + 6)
            {
               if (vh125_confirm10_enabled)
               {
                  const unsigned char vh125_mask = 0x02U;
                  if ((vh107_pad->padbits[0] & vh125_mask) != 0U)
                     return 381;
                  PerPadCReleased(vh107_pad);
                  if ((vh107_pad->padbits[0] & vh125_mask) == 0U)
                     return 382;
                  if (fprintf(vh107_pad_log,
                      "VH_PAD frame=%d button=%c action=RELEASE\n",
                      frame, 'C') <= 0)
                     return 383;
                  if (fprintf(vh109_state_log,
                      "VH_PADSTATE frame=%d button=%c active_low_bit=1\n",
                      frame, 'C') <= 0)
                     return 384;
               }
            }
'''

def instrument_private_tenth_confirm(stage124: bytes) -> bytes:
    source = stage124.decode("utf-8")
    if source.count(MODE_START) != 1 or source.count(MODE_END) != 1:
        raise ValueError("unpinned Stage124 private-frame branch")
    start = source.index(MODE_START)
    end = source.index(MODE_END, start) + len(MODE_END)
    mode = source[start:end]
    if "VH_SATURN_CONFIRM_AT_FRAME10" in mode or "vh125_confirm_at10" in mode:
        raise ValueError("Stage125 tenth confirm already instrumented")
    if mode.count("frames > 108000") != 1 or mode.count("YabauseEmulate()") != 1:
        raise ValueError("Stage125 requires the exact Stage124 108,000-frame cap")
    if mode.count(NINTH_SETUP_END) != 1 or mode.count(EMULATE_START) != 1:
        raise ValueError("Stage124 ninth-confirm source anchors differ")
    mode = mode.replace("frames > 108000", "frames > 120000", 1)
    mode = mode.replace(NINTH_SETUP_END, NINTH_SETUP_END + SETUP_CONFIRM10, 1)
    mode = mode.replace(EMULATE_START, CONFIRM10_PRESS + CONFIRM10_RELEASE + EMULATE_START, 1)
    for token, count in (
        ("VH_SATURN_CONFIRM_AT_FRAME10", 1),
        ("VH_SATURN_CONFIRM10_ENABLED", 1),
        ("vh125_confirm_at10", 4),
        ("vh125_confirm10_enabled", 4),
        ("PerPadCPressed(vh107_pad);", 10),
        ("PerPadCReleased(vh107_pad);", 10),
        ("VH_PAD frame=%d button=%c action=PRESS", 10),
        ("VH_PAD frame=%d button=%c action=RELEASE", 10),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=0", 10),
        ("VH_PADSTATE frame=%d button=%c active_low_bit=1", 10),
        ("frames > 120000", 1),
        ("YabauseEmulate()", 1),
    ):
        if mode.count(token) != count:
            raise ValueError("incomplete Stage125 tenth-confirm instrumentation: " + token)
    if "frames > 108000" in mode:
        raise ValueError("Stage125 retained the old 108,000-frame bound")
    result = source[:start] + mode + source[end:]
    if source.count("vh101_snapshot(") != result.count("vh101_snapshot("):
        raise ValueError("Stage125 changed inherited video capture")
    if source.count("vh102_snapshot(") != result.count("vh102_snapshot("):
        raise ValueError("Stage125 changed inherited SH2 capture")
    return result.encode("utf-8")

def instrument_full_private_tenth_confirm(raw: bytes) -> bytes:
    stage124 = instrument_full_private_ninth_confirm(raw)
    stage125 = instrument_private_tenth_confirm(stage124)
    source = stage125.decode("utf-8")
    for token in (
        "VH_SATURN_START_AT_FRAME", "VH_SATURN_CONFIRM_AT_FRAME8",
        "VH_SATURN_CONFIRM8_ENABLED", "VH_SATURN_CONFIRM_AT_FRAME9",
        "VH_SATURN_CONFIRM9_ENABLED", "VH_SATURN_CONFIRM_AT_FRAME10",
        "VH_SATURN_CONFIRM10_ENABLED", "frames > 120000", "frames.stats",
        "video-state.txt", "sh2-window.txt", "pad-state.txt",
    ):
        if token not in source:
            raise ValueError("incomplete composed Stage125 runner: " + token)
    return stage125

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if (args.source.name != "yui.cpp" or args.output.suffix != ".cpp"
                or args.output.exists() or args.source.resolve() == args.output.resolve()):
            raise ValueError("unsafe pinned source paths")
        result = instrument_full_private_tenth_confirm(args.source.read_bytes())
        with args.output.open("xb") as stream:
            stream.write(result)
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("STAGE125_TENTH_CONFIRM_PATCH_REJECTED", type(exc).__name__, str(exc),
              file=sys.stderr)
        return 1
    print("STAGE125_TENTH_CONFIRM_RUNNER_READY")
    return 0

if __name__ == "__main__":
    sys.exit(main())
