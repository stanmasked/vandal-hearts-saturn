#!/usr/bin/env python3
"""Stage64: audit the hovered movement-cost HUD on real NeXium guest PNGs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from tools.nexium_selected_unit_hud import DARK, HELP, _sample
from tools.nexium_tactical_action import (
    INITIAL, AFTER_SCOUT_MOVE, _center, _near, _require_state, _selected_marker,
)
from tools.nexium_visual_digest import decode, similar

GOLD = (251, 220, 90)
X, Y = 500, 670
GLYPHS = {
    "C": (3,4,4,4,3), "O": (2,5,5,5,2), "S": (3,4,2,1,6),
    "T": (7,2,2,2,2), "L": (4,4,4,4,7), "E": (7,4,6,4,7),
    "F": (7,4,6,4,4),
    "0": (7,5,5,5,7), "1": (2,6,2,2,7), "2": (7,1,7,4,7),
    "3": (7,1,7,1,7), "4": (5,5,7,1,1), "5": (7,4,7,1,7),
    "6": (7,4,7,5,7), "7": (7,1,1,1,1), "8": (7,5,7,5,7),
    "9": (7,5,7,1,7), " ": (0,0,0,0,0),
}
TEXT_FOOTPRINT = "COST 2 LEFT 2"


def _bits(text):
    if not isinstance(text, str) or not text or len(text) > 18:
        raise ValueError("unsupported movement preview text width")
    bits = {}
    for i, char in enumerate(text):
        if char not in GLYPHS:
            raise ValueError("unsupported movement preview glyph " + repr(char))
        for y, mask in enumerate(GLYPHS[char]):
            for x in range(3):
                bits[f"{i}-{x}-{y}"] = bool(mask & (1 << (2-x)))
    return bits


def expect_move_preview(image, cost, remaining):
    if (not isinstance(cost, int) or isinstance(cost, bool) or
            not isinstance(remaining, int) or isinstance(remaining, bool) or
            cost < 0 or remaining < 0 or cost > 999 or remaining > 999):
        raise ValueError("unsupported movement preview values")
    text = f"COST {cost} LEFT {remaining}"
    bits = _bits(text)
    # The guest's fractional vertical scale can round the final 2px logical
    # glyph row one physical pixel lower than the preceding rows. Sample its
    # interior separately, while keeping both calibrated vertical baselines.
    # Every lit AND blank cell must match; broad color scans are insufficient.
    for offset_y in (-3, -1):
        positions = {
            key: (X + 8*int(key.split("-")[0]) + 2*int(key.split("-")[1]),
                  Y + 2*int(key.split("-")[2]) + 1 + offset_y +
                  (1 if int(key.split("-")[2]) == 4 else 0))
            for key in bits
        }
        observed = _sample(image, positions)
        if all(similar(observed[k], GOLD if lit else DARK) for k, lit in bits.items()):
            return True
    raise ValueError(f"movement preview bitmap mismatch COST {cost} LEFT {remaining}")


def expect_hidden(image, *, selected=False):
    background = DARK if selected else HELP
    bits = _bits(TEXT_FOOTPRINT)
    for offset_y in (-3, -1):
        positions = {
            key: (X + 8*int(key.split("-")[0]) + 2*int(key.split("-")[1]),
                  Y + 2*int(key.split("-")[2]) + 1 + offset_y +
                  (1 if int(key.split("-")[2]) == 4 else 0))
            for key in bits
        }
        observed = _sample(image, positions)
        if any(not similar(pixel, background) for pixel in observed.values()):
            label = "selected panel" if selected else "no-selection help strip"
            raise ValueError("ghost movement preview on " + label)
    return True


def verify_folder(folder):
    report = json.loads((folder / "action-evidence.json").read_text("utf8"))
    if report.get("action_passed") is not True:
        raise ValueError("guest tactical move receipt not successful")
    if report.get("initial_fingerprint") != INITIAL or report.get("after_move_fingerprint") != AFTER_SCOUT_MOVE:
        raise ValueError("movement preview evidence has wrong tactical fingerprints")
    selected_name = report.get("selected_proof")
    aimed_name = report.get("aimed_proof")
    moved_name = report.get("moved_proof")
    if selected_name not in ("action-selected.png", "action-selected-retry.png"):
        raise ValueError("invalid selected frame filename")
    if aimed_name not in {f"action-aim-{i}.png" for i in range(1, 9)}:
        raise ValueError("invalid legal destination frame filename")
    if moved_name not in ("action-moved.png", "action-moved-retry.png"):
        raise ValueError("invalid committed move frame filename")

    with Image.open(folder / "nexium-window.png") as initial, \
         Image.open(folder / selected_name) as selected, \
         Image.open(folder / aimed_name) as aimed, \
         Image.open(folder / moved_name) as moved:
        _require_state(initial, INITIAL)
        scale = decode(initial, INITIAL)
        start = _center(initial)
        target = (start[0] + 40*scale["scale_x"], start[1] + 20*scale["scale_y"])
        _require_state(selected, INITIAL)
        _require_state(aimed, INITIAL)
        _require_state(moved, AFTER_SCOUT_MOVE)
        if not _selected_marker(selected, start):
            raise ValueError("selected Scout outline missing")
        if not _selected_marker(aimed, start):
            raise ValueError("selected Scout outline missing on movement preview frame")
        if not _near(_center(aimed), target):
            raise ValueError("movement preview frame cursor is not on adjacent destination")
        expect_hidden(initial, selected=False)
        expect_hidden(selected, selected=True)
        expect_move_preview(aimed, 2, 2)
        expect_hidden(moved, selected=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-dir", type=Path, required=True)
    args = parser.parse_args()
    verify_folder(args.verify_dir)
    print("VH_MOVE_PREVIEW verified=true cost=2 remaining=2 hidden=no_selection/spent_move")


if __name__ == "__main__":
    main()
