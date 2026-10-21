#!/usr/bin/env python3
"""Stage59: verify after-strike enemy HP bitmap on real NeXium PNGs."""
from __future__ import annotations
import argparse
from pathlib import Path
from PIL import Image

from tools.nexium_target_damage_hud import verify_folder as verify_damage
from tools.nexium_attack_preview_hud import _final_aim
from tools.nexium_duel_victory import _sample
from tools.nexium_selected_unit_hud import DIGITS, WHITE, DARK, HELP
from tools.nexium_visual_digest import similar

PANEL={"h":(1141,676),"p":(1149,676)}
DIGIT_X=1164

def _color_check(image,want):
    actual=_sample(image,PANEL)
    for label,observed in actual.items():
        if not similar(observed,want):
            raise ValueError("target remaining HUD pixel mismatch "+label+
                             " want="+str(want)+" observed="+str(observed))

def _digits(image,hp):
    if hp<0 or hp>99:raise ValueError("invalid predicted remaining HP")
    bits={}
    for i,ch in enumerate(str(hp)):
        for y,mask in enumerate(DIGITS[ch]):
            for x in range(3):
                bits[f"{i}-{x}-{y}"]=bool(mask & (1 << (2-x)))
    best=0
    for dx in (-1,0,1):
        for dy in (-3,-2,-1,0):
            pos={}
            for key in bits:
                i,x,y=(int(v) for v in key.split("-"))
                pos[key]=(DIGIT_X+8*i+2*x+1+dx,675+2*y+1+dy)
            observed=_sample(image,pos)
            score=sum(similar(observed[k],WHITE if lit else DARK)
                      for k,lit in bits.items())
            best=max(best,score)
            if score==len(bits):return True
    raise ValueError("target remaining HP bitmap mismatch expected="+
                     str(hp)+" bits="+str(best)+"/"+str(len(bits)))

def expect_visible(image,hp):
    _color_check(image,WHITE)
    return _digits(image,hp)

def expect_hidden(image,*,enemy_visible):
    _color_check(image,DARK if enemy_visible else HELP)
    return True

def verify_folder(duel,defeat):
    # All older audits run independently on the same real screenshots.
    verify_damage(duel,defeat)
    with Image.open(duel/"nexium-window.png") as initial, \
         Image.open(_final_aim(duel,"action-duel-aim-")) as first_aim, \
         Image.open(duel/"action-duel-attacked.png") as first_hit, \
         Image.open(_final_aim(duel,"action-victory-round4-aim-nav-")) as last_aim, \
         Image.open(duel/"action-victory-round4-attacked.png") as won, \
         Image.open(defeat/"action-defeat-round-8.png") as lost:
        expect_hidden(initial,enemy_visible=False)
        expect_visible(first_aim,14)
        expect_hidden(first_hit,enemy_visible=True)
        expect_visible(last_aim,0)
        expect_hidden(won,enemy_visible=False)
        expect_hidden(lost,enemy_visible=False)
    return True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duel",type=Path,required=True)
    parser.add_argument("--defeat",type=Path,required=True)
    args=parser.parse_args()
    verify_folder(args.duel,args.defeat)
    print("VH_TARGET_REMAINING verified=true first_hp_after=14 lethal_hp_after=0 hidden_spent_terminal=true")

if __name__=="__main__": main()
