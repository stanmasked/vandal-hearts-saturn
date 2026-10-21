#!/usr/bin/env python3
"""Stage54: independent image-only audit of original ROM-free attack preview HUD.

Checks guest-origin PNGs captured by existing Stage44/Stage50 input routes.
NEVER accepts a JSON success field in place of the actual framebuffer pixels.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image

from tools.nexium_attack_action import INITIAL_DUEL, ATTACKED_DUEL
from tools.nexium_duel_victory import ROUND4, VICTORY, _sample
from tools.nexium_tactical_action import _center, _near, _require_state, _selected_marker
from tools.nexium_visual_digest import similar

GREEN = (117,221,109)
PURPLE = (179,103,244)
DARK = (23,30,41)
GOLD = (251,220,90)
HELP = (45,64,83)
BAR = {
    "left": (160,686), "right": (280,686),
    "border": (150,676),
}


def _expect_forecast(image, *, lethal=False):
    rgb = _sample(image, BAR)
    correct = {"left":PURPLE if lethal else GREEN,
               "right":PURPLE,
               "border":GOLD if lethal else DARK}
    for name, expected in correct.items():
        if not similar(rgb[name],expected):
            raise ValueError("attack preview HUD pixel mismatch: " + name +
                             " expected=" + str(expected) +
                             " observed=" + str(rgb[name]))
    return True


def _expect_hidden(image):
    rgb = _sample(image, BAR)
    for name in ("left","right","border"):
        if not similar(rgb[name],HELP):
            raise ValueError("attack preview HUD failed to disappear: "+name)
    return True


def _final_aim(folder, prefix):
    # The pre-existing NeXium controllers can overshoot or miss a keypress;
    # only the LAST observed aim frame proves a correct target.
    possibilities = []
    for child in folder.iterdir():
        name = child.name
        if name.startswith(prefix) and name.endswith(".png"):
            suffix = name[len(prefix):-4]
            if suffix.isdecimal() and 1 <= int(suffix) <= 12:
                possibilities.append((int(suffix),child))
    if not possibilities:
        raise ValueError("real NeXium aim screenshot absent: "+prefix)
    possibilities.sort(key=lambda item:item[0])
    if [i for i,_ in possibilities] != list(range(1,len(possibilities)+1)):
        raise ValueError("incomplete or duplicated NeXium aim PNG sequence")
    return possibilities[-1][1]


def verify_folder(duel_folder, victory_folder):
    data = json.loads((duel_folder/"attack-evidence.json").read_text("utf-8"))
    if data.get("attack_passed") is not True:
        raise ValueError("original real duel not verified")
    name = data.get("selected_proof")
    if name not in ("action-duel-selected.png","action-duel-selected-retry.png"):
        raise ValueError("duel selection proof invalid")

    with Image.open(duel_folder/"nexium-window.png") as initial, \
         Image.open(duel_folder/name) as selected, \
         Image.open(_final_aim(duel_folder,"action-duel-aim-")) as aimed, \
         Image.open(duel_folder/"action-duel-attacked.png") as hit:
        scout=_center(initial)
        raider=_center(aimed)
        _require_state(initial,INITIAL_DUEL)
        _require_state(selected,INITIAL_DUEL)
        _require_state(aimed,INITIAL_DUEL)
        _require_state(hit,ATTACKED_DUEL)
        if not (_selected_marker(selected,scout) and _selected_marker(aimed,scout)):
            raise ValueError("unselected attacker in HUD real-aim screenshot")
        if not _near(_center(aimed),_center(hit)):
            raise ValueError("HUD aim does not match actual attacked enemy")
        if not raider[0]>scout[0]+12:
            raise ValueError("HUD aim does not point to adjacent Raider")
        _expect_hidden(selected)
        _expect_forecast(aimed,lethal=False)
        _expect_hidden(hit)  # consumed attack can no longer be previewed

    victory = json.loads((victory_folder/"victory-evidence.json").read_text("utf-8"))
    if victory.get("victory_passed") is not True:
        raise ValueError("prior Stage50 real victory not verified")
    with Image.open(_final_aim(victory_folder,"action-victory-round4-aim-nav-")) as aimed, \
         Image.open(victory_folder/"action-victory-round4-attacked.png") as hit:
        _require_state(aimed,ROUND4)
        _require_state(hit,VICTORY)
        if not _near(_center(aimed),_center(hit)):
            raise ValueError("lethal HUD preview not aimed at actual final target")
        _expect_forecast(aimed,lethal=True)
        _expect_hidden(hit)
    return True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duel",type=Path,required=True)
    parser.add_argument("--victory",type=Path,required=True)
    args=parser.parse_args()
    verify_folder(args.duel,args.victory)
    print("VH_PREVIEW_HUD verified=true hit=20->14 lethal=2->0 hidden_after_attack=true")


if __name__=="__main__":
    main()
