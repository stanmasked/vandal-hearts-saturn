#!/usr/bin/env python3
"""Stage56: re-open REAL NeXium PNGs to prove enemy-hover HUD pixels.

ROM-free tactical game. JSON receipts cannot substitute for actual screenshots.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from tools.nexium_attack_action import INITIAL_DUEL, ATTACKED_DUEL
from tools.nexium_second_round import ROUND2, ROUND2_ATTACK
from tools.nexium_duel_victory import ROUND4, VICTORY, _sample
from tools.nexium_duel_defeat import ROUND_HASHES
from tools.nexium_attack_preview_hud import _final_aim
from tools.nexium_tactical_action import _require_state, _center, _near, _selected_marker
from tools.nexium_selected_unit_hud import WHITE, DARK, HELP, DIGITS
from tools.nexium_visual_digest import similar

RED = (239, 79, 76)
PANEL = {
    "marker": (1010, 682), "body": (1268, 705),
    "name": (1021, 676), "hp": (1023, 691),
    "attack": (1080, 691), "defense": (1141, 691),
    "range": (1205, 691),
}


def _expect_colors(image, expected):
    observed = _sample(image, PANEL)
    for key, rgb in expected.items():
        if not similar(observed[key], rgb):
            raise ValueError("enemy HUD pixel mismatch: " + key +
                             " expected=" + str(rgb) +
                             " observed=" + str(observed[key]))
    return True


def _expect_digits(image, hp, start_x, field):
    if not (0 < hp <= 99):
        raise ValueError("unsupported enemy "+field)
    expected = {}
    for index, digit in enumerate(str(hp)):
        for y, mask in enumerate(DIGITS[digit]):
            for x in range(3):
                expected[f"{index}-{x}-{y}"] = bool(mask & (1 << (2-x)))
    for offset_y in (-3, -2, -1, 0):
        positions = {}
        for key in expected:
            i, x, y = (int(v) for v in key.split("-"))
            positions[key] = (start_x + 2*x + 8*i + 1,
                              690 + 2*y + 1 + offset_y)
        actual = _sample(image, positions)
        if all(similar(actual[k], WHITE if lit else DARK)
               for k, lit in expected.items()):
            return True
    raise ValueError("enemy HUD "+field+" digit mismatch: " + str(hp))


def expect_visible(image, hp, *, attack=6, defense=2, attack_range=1):
    _expect_colors(image,{
        "marker": RED, "body": DARK,
        "name": WHITE, "hp": WHITE, "attack": WHITE,
        "defense": WHITE, "range": WHITE,
    })
    # Exact bitmap bitmaps, not just visible labels: a forged ATK, DEF or
    # RNG digit must fail even when battle hash and HP were correct.
    for field, value, glyph_x in (
        ("HP", hp, 1022+8*3),
        ("ATK", attack, 1077+8*4),
        ("DEF", defense, 1140+8*4),
        ("RNG", attack_range, 1204+8*4),
    ):
        _expect_digits(image,value,glyph_x,field)
    return True


def expect_hidden(image):
    return _expect_colors(image,{key: HELP for key in PANEL})


def _receipt(folder,name):
    return json.loads((folder/name).read_text("utf8"))


def verify_folder(duel,defeat):
    attack = _receipt(duel,"attack-evidence.json")
    victory = _receipt(duel,"victory-evidence.json")
    round2 = _receipt(duel,"round2-evidence.json")
    loss = _receipt(defeat,"defeat-evidence.json")
    if attack.get("attack_passed") is not True or victory.get("victory_passed") is not True:
        raise ValueError("missing real duel and Victory pass receipts")
    if loss.get("defeat_passed") is not True:
        raise ValueError("missing real Defeat pass receipt")
    selected = attack.get("selected_proof")
    new_round = round2.get("ended_proof")
    round2_selected = round2.get("selection_proof")
    if selected not in ("action-duel-selected.png","action-duel-selected-retry.png"):
        raise ValueError("untrusted Scout selection filename")
    if new_round not in ("action-round2-ended.png","action-round2-ended-retry.png"):
        raise ValueError("untrusted second-round ending filename")
    if round2_selected not in ("action-round2-selected.png","action-round2-selected-retry.png"):
        raise ValueError("untrusted second-round selection filename")
    with Image.open(duel/"nexium-window.png") as initial, \
         Image.open(duel/selected) as ally, \
         Image.open(_final_aim(duel,"action-duel-aim-")) as aim, \
         Image.open(duel/"action-duel-attacked.png") as attacked, \
         Image.open(duel/new_round) as new, \
         Image.open(duel/round2_selected) as second_ally, \
         Image.open(duel/"action-round2-attacked.png") as second_hit, \
         Image.open(_final_aim(duel,"action-victory-round4-aim-nav-")) as last_aim, \
         Image.open(duel/"action-victory-round4-attacked.png") as won, \
         Image.open(defeat/"action-defeat-round-8.png") as lost:
        cases = (
            (initial,INITIAL_DUEL),(ally,INITIAL_DUEL),(aim,INITIAL_DUEL),
            (attacked,ATTACKED_DUEL),(new,ROUND2),(second_ally,ROUND2),
            (second_hit,ROUND2_ATTACK),(last_aim,ROUND4),
            (won,VICTORY),(lost,ROUND_HASHES[-1]),
        )
        for frame, fingerprint in cases:
            _require_state(frame,fingerprint)
        scout=_center(initial)
        raider=_center(aim)
        if not raider[0]>scout[0]+12:
            raise ValueError("enemy HUD proof does not aim at Raider")
        for frame in (aim,attacked,new,second_hit,last_aim,won):
            if not _near(_center(frame),raider):
                raise ValueError("enemy HUD proof cursor not on Raider")
        for frame in (ally,aim,attacked,second_hit,last_aim):
            if not _selected_marker(frame,scout):
                raise ValueError("enemy HUD proof lost actual selected Scout")
        expect_hidden(initial)
        expect_hidden(ally)
        expect_visible(aim,20)
        expect_visible(attacked,14)
        expect_visible(new,14)
        expect_hidden(second_ally)
        expect_visible(second_hit,8)
        expect_visible(last_aim,2)
        expect_hidden(won)
        expect_hidden(lost)
    return True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duel",type=Path,required=True)
    parser.add_argument("--defeat",type=Path,required=True)
    args=parser.parse_args()
    verify_folder(args.duel,args.defeat)
    print("VH_ENEMY_HOVER verified=true Raider_HP=20,14,8,2 hidden_on_ally=true hidden_on_victory_defeat=true")


if __name__=="__main__":
    main()
