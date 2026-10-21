#!/usr/bin/env python3
"""Stage60: real NeXium pixel audit of post-attack HP green/red split."""
from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image

from tools.nexium_target_remaining_hud import verify_folder as verify_remaining
from tools.nexium_attack_preview_hud import _final_aim
from tools.nexium_duel_victory import _sample
from tools.nexium_selected_unit_hud import DARK,HELP
from tools.nexium_visual_digest import similar

GREEN=(117,221,109)
RED=(239,79,76)
X,Y,WIDTH=1020,707,220

def verify_colors(image,*,current_hp=None,hp_after=None,enemy_visible=False):
    if current_hp is None:
        if hp_after is not None:
            raise ValueError("hidden bar cannot have predicted HP")
        base=DARK if enemy_visible else HELP
        positions={str(x):(x,Y) for x in range(X+4,X+WIDTH-4,6)}
        observed=_sample(image,positions)
        if any(not similar(v,base) for v in observed.values()):
            raise ValueError("ghost projected health bar in hidden state")
        return True
    if not (0<current_hp<=999 and hp_after is not None and 0<=hp_after<current_hp):
        raise ValueError("invalid legal projected health")
    green_width=hp_after*WIDTH//current_hp
    samples={}
    wanted={}
    # Ignore boundary +/- 3px where calibrated scaling can round colors,
    # but compare the green/red semantic colors throughout the full bar.
    for x in range(X+4,X+WIDTH-4,4):
        if abs(x-(X+green_width))<=3:continue
        key=str(x)
        samples[key]=(x,Y)
        wanted[key]=GREEN if x<X+green_width else RED
    observed=_sample(image,samples)
    for key,value in observed.items():
        if not similar(value,wanted[key]):
            raise ValueError("projected bar mismatch x="+key+
                             " expected="+str(wanted[key])+" observed="+str(value)+
                             " remaining="+str(hp_after)+"/"+str(current_hp))
    return True

def verify_folder(duel,defeat):
    # Independently re-run all Stage54-59 registered guest PNG gates.
    verify_remaining(duel,defeat)
    with Image.open(duel/"nexium-window.png") as initial, \
         Image.open(_final_aim(duel,"action-duel-aim-")) as first_aim, \
         Image.open(duel/"action-duel-attacked.png") as hit, \
         Image.open(_final_aim(duel,"action-victory-round4-aim-nav-")) as lethal_aim, \
         Image.open(duel/"action-victory-round4-attacked.png") as victory, \
         Image.open(defeat/"action-defeat-round-8.png") as defeat_frame:
        verify_colors(initial)
        verify_colors(first_aim,current_hp=20,hp_after=14)
        verify_colors(hit,enemy_visible=True)
        verify_colors(lethal_aim,current_hp=2,hp_after=0)
        verify_colors(victory)
        verify_colors(defeat_frame)
    return True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duel",type=Path,required=True)
    parser.add_argument("--defeat",type=Path,required=True)
    args=parser.parse_args()
    verify_folder(args.duel,args.defeat)
    print("VH_PROJECTED_BAR verified=true first=14of20 lethal=0of2 hidden_spent_terminal=true")

if __name__=="__main__":
    main()
