#!/usr/bin/env python3
"""Stage57: verify attack availability cue on REAL NeXium PNG captures."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image
from tools.nexium_enemy_hover_hud import verify_folder as verify_enemy_hud, _receipt
from tools.nexium_attack_preview_hud import _final_aim
from tools.nexium_attack_action import INITIAL_DUEL, ATTACKED_DUEL
from tools.nexium_second_round import ROUND2, ROUND2_ATTACK
from tools.nexium_duel_victory import ROUND4, VICTORY, _sample
from tools.nexium_duel_defeat import ROUND_HASHES
from tools.nexium_tactical_action import _require_state
from tools.nexium_selected_unit_hud import HELP
from tools.nexium_visual_digest import similar

# Each color is an independent native battle-view state. The cue stays inside
# Stage56's card and outside Stage54/55 and visual digest sample positions.
COLORS = {
    "hidden": HELP,
    "inspect": (74, 94, 111),
    "ready": (251, 220, 90),
    "spent": (179, 103, 244),
    "blocked": (116, 77, 88),
}
CUE = {"attack_cue": (1252, 679)}

def expect_cue(image, state):
    if state not in COLORS:
        raise ValueError("unknown attack cue expectation")
    observed = _sample(image, CUE)["attack_cue"]
    wanted = COLORS[state]
    if not similar(observed,wanted):
        raise ValueError("attack cue pixel mismatch: "+state+
                         " expected="+str(wanted)+" observed="+str(observed))
    return True

def verify_folder(duel,defeat):
    # The Stage56 real PNG audit verifies the source proofs, full on-screen
    # battle digest, cursor location, selected state and accurate enemy digits.
    verify_enemy_hud(duel,defeat)
    selected=_receipt(duel,"attack-evidence.json")["selected_proof"]
    ended=_receipt(duel,"round2-evidence.json")["ended_proof"]
    with Image.open(duel/"nexium-window.png") as initial, \
         Image.open(duel/selected) as ally, \
         Image.open(_final_aim(duel,"action-duel-aim-")) as aim, \
         Image.open(duel/"action-duel-attacked.png") as attacked, \
         Image.open(duel/ended) as second_round, \
         Image.open(duel/"action-round2-attacked.png") as round2_attack, \
         Image.open(_final_aim(duel,"action-victory-round4-aim-nav-")) as lethal_aim, \
         Image.open(duel/"action-victory-round4-attacked.png") as win, \
         Image.open(defeat/"action-defeat-round-8.png") as loss:
        cases=[
            (initial,INITIAL_DUEL,"hidden"),
            (ally,INITIAL_DUEL,"hidden"),
            (aim,INITIAL_DUEL,"ready"),
            (attacked,ATTACKED_DUEL,"spent"),
            (second_round,ROUND2,"inspect"),
            (round2_attack,ROUND2_ATTACK,"spent"),
            (lethal_aim,ROUND4,"ready"),
            (win,VICTORY,"hidden"),
            (loss,ROUND_HASHES[-1],"hidden"),
        ]
        for frame,hash_value,state in cases:
            _require_state(frame,hash_value)
            expect_cue(frame,state)
    return True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duel",type=Path,required=True)
    parser.add_argument("--defeat",type=Path,required=True)
    args=parser.parse_args()
    verify_folder(args.duel,args.defeat)
    print("VH_ATTACK_CUE verified=true ready_before_strike=true spent_after_strike=true inspect_after_endturn=true hidden_terminal=true")

if __name__=="__main__":
    main()
