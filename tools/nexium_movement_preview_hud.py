#!/usr/bin/env python3
"""Stage64 pixel audit of hovered move cost on real NeXium guest screenshots."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image
from tools.nexium_attack_action import INITIAL_DUEL, ATTACKED_DUEL
from tools.nexium_duel_victory import _sample
from tools.nexium_attack_preview_hud import _final_aim
from tools.nexium_tactical_action import _center, _near, _require_state, _selected_marker
from tools.nexium_visual_digest import decode, similar

PANEL = (23, 30, 41)
BACKGROUND = (14, 19, 32)
GREEN = (117, 221, 109)
WHITE = (220, 233, 238)
GLYPHS = {
    "0": (7,5,5,5,7), "1": (2,6,2,2,7), "2": (7,1,7,4,7),
    "3": (7,1,7,1,7), "4": (5,5,7,1,1), "5": (7,4,7,1,7),
    "6": (7,4,7,5,7), "7": (7,1,1,1,1), "8": (7,5,7,5,7),
    "9": (7,5,7,1,7), "C": (3,4,4,4,3), "O": (2,5,5,5,2),
    "S": (3,4,2,1,6), "T": (7,2,2,2,2), "L": (4,4,4,4,7),
    "E": (7,4,6,4,7), "F": (7,4,6,4,4), " ": (0,0,0,0,0),
}
TEXT_X, TEXT_Y = 36, 610
PROOF = "action-duel-move-preview.png"
RETURN_PROOF = "action-duel-move-preview-return.png"


def _text_bits(text: str):
    bits = {}
    if not text or len(text) > 18 or any(ch not in GLYPHS for ch in text):
        raise ValueError("unsupported movement preview text")
    for i, char in enumerate(text):
        for y, mask in enumerate(GLYPHS[char]):
            for x in range(3):
                bits[f"{i}-{x}-{y}"] = bool(mask & (1 << (2-x)))
    return bits


def expect_visible(image, *, cost=1, remaining=3):
    if not (1 <= cost <= 99 and 0 <= remaining <= 99):
        raise ValueError("unsupported movement preview values")
    text = f"COST {cost} LEFT {remaining}"
    if len(text) > 18:
        raise ValueError("movement preview text would be truncated")
    samples = _sample(image, {"panel": (18, 602), "marker": (24, 620)})
    if not similar(samples["panel"], PANEL):
        raise ValueError("movement preview panel background missing")
    if not similar(samples["marker"], GREEN):
        raise ValueError("movement preview legal-destination marker missing")
    bits = _text_bits(text)
    for offset_y in (-3, -1):
        positions = {
            key: (TEXT_X + 8*int(key.split("-")[0]) +
                  2*int(key.split("-")[1]) + 1,
                  TEXT_Y + 2*int(key.split("-")[2]) + 1 + offset_y)
            for key in bits
        }
        observed = _sample(image, positions)
        if all(similar(observed[k], WHITE if lit else PANEL)
               for k, lit in bits.items()):
            return True
    raise ValueError("movement preview COST/LEFT glyph mismatch: " + text)


def expect_hidden(image):
    probes = {"panel": (18, 602), "marker": (24, 620),
              "text_on": (37, 608), "text_tail": (139, 618)}
    observed = _sample(image, probes)
    for name, rgb in observed.items():
        if not similar(rgb, BACKGROUND):
            raise ValueError("ghost movement preview " + name +
                             " expected=" + str(BACKGROUND) +
                             " observed=" + str(rgb))
    return True


def verify_folder(duel: Path):
    receipt = json.loads((duel / "attack-evidence.json").read_text("utf8"))
    if receipt.get("attack_passed") is not True:
        raise ValueError("real NeXium duel attack was not independently verified")
    if receipt.get("movement_preview_proof") != PROOF:
        raise ValueError("movement preview screenshot receipt is missing or untrusted")
    if receipt.get("movement_preview_return_proof") != RETURN_PROOF:
        raise ValueError("movement preview return screenshot receipt is missing or untrusted")
    selected_name = receipt.get("selected_proof")
    if selected_name not in ("action-duel-selected.png",
                             "action-duel-selected-retry.png"):
        raise ValueError("invalid selected screenshot proof")
    with Image.open(duel / "nexium-window.png") as initial, \
         Image.open(duel / selected_name) as selected, \
         Image.open(duel / PROOF) as preview, \
         Image.open(duel / RETURN_PROOF) as returned, \
         Image.open(_final_aim(duel, "action-duel-aim-")) as aim, \
         Image.open(duel / "action-duel-attacked.png") as attacked:
        for frame in (initial, selected, preview, returned, aim):
            _require_state(frame, INITIAL_DUEL)
        _require_state(attacked, ATTACKED_DUEL)
        start = _center(initial)
        scale = decode(initial, INITIAL_DUEL)
        expected_up = (start[0], start[1] - 20 * scale["scale_y"])
        if not _near(_center(preview), expected_up, tx=12, ty=12):
            raise ValueError("preview evidence is not the adjacent tile above Scout")
        if not _near(_center(returned), start):
            raise ValueError("return evidence did not restore the Scout cursor")
        for frame in (selected, preview, returned, aim, attacked):
            if not _selected_marker(frame, start):
                raise ValueError("movement preview sequence lost selected Scout")
        expect_hidden(initial)
        expect_hidden(selected)
        expect_visible(preview, cost=1, remaining=3)
        expect_hidden(returned)
        expect_hidden(aim)
        expect_hidden(attacked)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duel", type=Path, required=True)
    args = parser.parse_args()
    verify_folder(args.duel)
    print("VH_MOVE_PREVIEW verified=true cost=1 remaining=3 hidden_on_invalid=true")


if __name__ == "__main__":
    main()
