#!/usr/bin/env python3
"""Stage55: verify selected-unit stats on ACTUAL registered NeXium frames.

Stage55 is an original font-free HUD; not original Sega Saturn content.
Reopen independently captured X11 screenshots, never accept JSON alone.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image

from tools.nexium_attack_action import INITIAL_DUEL, ATTACKED_DUEL
from tools.nexium_second_round import ROUND2
from tools.nexium_duel_victory import ROUND4, VICTORY, _sample
from tools.nexium_duel_defeat import ROUND_HASHES
from tools.nexium_tactical_action import _require_state, _selected_marker, _center
from tools.nexium_visual_digest import similar

BLUE = (63,167,239)
DARK = (23,30,41)
HELP = (45,64,83)
READY = (76,222,230)
ACTED = (179,103,244)
NOT_MOVED = (74,94,111)
WHITE = (220,233,238)

# Black/white 3x5 pixel font used by the native SDL renderer.
DIGITS = {
    "0": (7,5,5,5,7), "1": (2,6,2,2,7), "2": (7,1,7,4,7),
    "3": (7,1,7,1,7), "4": (5,5,7,1,1), "5": (7,4,7,1,7),
    "6": (7,4,7,5,7), "7": (7,1,1,1,1), "8": (7,5,7,5,7),
    "9": (7,5,7,1,7),
}
PANEL = {
    "marker": (357,682), "ready_or_acted": (960,688),
    "not_moved": (979,688), "body": (365,704),
    # White glyph pixels, verified only when a live ally is selected:
    "hp_label": (501,684), "attack_label": (606,684),
    "defense_label": (725,684), "range_label": (840,684),
}


def _check_colors(image, expected):
    read = _sample(image, PANEL)
    for name, want in expected.items():
        if not similar(read[name],want):
            raise ValueError("unit HUD pixel mismatch "+name+
                             " expected="+str(want)+" observed="+str(read[name]))
    return True


def _check_digits(image, hp):
    if not 0 <= hp <= 99:
        raise ValueError("unsupported HP numeral")
    # SDL: unit_stat_text("HP " + decimal HP, x500, y683), scale 2,
    # each glyph advances 8 logical pixels. Check every onscreen 2x2 cell.
    digits=str(hp)
    positions={}
    for i, digit in enumerate(digits):
        glyph=DIGITS[digit]
        base=500 + 8 * (3+i)
        for y,mask in enumerate(glyph):
            for x in range(3):
                positions[f"{i}-{x}-{y}"]=(base+2*x+1,683+2*y+1)
    observed=_sample(image,positions)
    for i,digit in enumerate(digits):
        for y,mask in enumerate(DIGITS[digit]):
            for x in range(3):
                expected=WHITE if (mask & (1 << (2-x))) else DARK
                key=f"{i}-{x}-{y}"
                if not similar(observed[key],expected):
                    raise ValueError("unit HUD HP digit mismatch: "+
                                     str(hp)+" pixel="+key+
                                     " observed="+str(observed[key]))
    return True


def expect_visible(image, hp, *, attacked=False):
    expect={
        "marker":BLUE,
        "ready_or_acted":ACTED if attacked else READY,
        "not_moved":NOT_MOVED,
        "body":DARK,
        "hp_label":WHITE, "attack_label":WHITE,
        "defense_label":WHITE, "range_label":WHITE,
    }
    _check_colors(image,expect)
    _check_digits(image,hp)
    return True


def expect_hidden(image):
    return _check_colors(image,{key:HELP for key in PANEL})


def _candidate(folder, name, retry=None):
    first=folder/name
    if first.is_file(): return first
    if retry is not None:
        alternate=folder/retry
        if alternate.is_file(): return alternate
    raise ValueError("missing real NeXium stat HUD PNG "+name)


def verify_folder(duel, defeat):
    attack=json.loads((duel/"attack-evidence.json").read_text("utf8"))
    victory=json.loads((duel/"victory-evidence.json").read_text("utf8"))
    loss=json.loads((defeat/"defeat-evidence.json").read_text("utf8"))
    if not attack.get("attack_passed") or not victory.get("victory_passed"):
        raise ValueError("real first-strike and Victory evidence not successful")
    if not loss.get("defeat_passed"):
        raise ValueError("real Defeat evidence not successful")
    selected_name=attack.get("selected_proof")
    if selected_name not in ("action-duel-selected.png",
                             "action-duel-selected-retry.png"):
        raise ValueError("invalid duel selected filename")
    round2_report=json.loads((duel/"round2-evidence.json").read_text("utf8"))
    round2_name=round2_report.get("selection_proof")
    ended_name=round2_report.get("ended_proof")
    if round2_name not in ("action-round2-selected.png",
                           "action-round2-selected-retry.png"):
        raise ValueError("invalid second-round selected filename")
    if ended_name not in ("action-round2-ended.png",
                          "action-round2-ended-retry.png"):
        raise ValueError("invalid second-round endturn filename")
    fourth_name=victory.get("round4_selection_proof")
    if fourth_name not in ("action-victory-round4-selected.png",
                           "action-victory-round4-selected-retry.png"):
        raise ValueError("invalid fourth-round selected filename")
    with Image.open(duel/"nexium-window.png") as initial, \
         Image.open(duel/selected_name) as selected, \
         Image.open(duel/"action-duel-attacked.png") as attacked, \
         Image.open(duel/ended_name) as new_round, \
         Image.open(duel/round2_name) as round2, \
         Image.open(duel/fourth_name) as fourth, \
         Image.open(duel/"action-victory-round4-attacked.png") as won, \
         Image.open(defeat/"action-defeat-round-8.png") as lost:
        states=((initial,INITIAL_DUEL),(selected,INITIAL_DUEL),
                (attacked,ATTACKED_DUEL),(new_round,ROUND2),
                (round2,ROUND2),(fourth,ROUND4),
                (won,VICTORY),(lost,ROUND_HASHES[-1]))
        for frame,hash_value in states:
            _require_state(frame,hash_value)
        expect_hidden(initial)
        scout=_center(initial)
        for frame in (selected,attacked,round2,fourth):
            if not _selected_marker(frame,scout):
                raise ValueError("guest HUD visible without selected Scout")
        expect_visible(selected,22)
        expect_visible(attacked,22,attacked=True)
        expect_hidden(new_round)
        expect_visible(round2,19)
        expect_visible(fourth,13)
        expect_hidden(won)
        expect_hidden(lost)
    return True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duel",type=Path,required=True)
    parser.add_argument("--defeat",type=Path,required=True)
    args=parser.parse_args()
    verify_folder(args.duel,args.defeat)
    print("VH_SELECTED_HUD verified=true HP=22,19,13 "+
          "ready_and_acted=true hidden_after_turn=true "+
          "hidden_on_victory_defeat=true")


if __name__=="__main__":
    main()
