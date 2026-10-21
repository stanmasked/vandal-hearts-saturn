#!/usr/bin/env python3
"""Stage58: strict bitmap audit of damage forecast on real NeXium screenshots."""
from __future__ import annotations
import argparse
from pathlib import Path
from PIL import Image

from tools.nexium_enemy_attack_cue import verify_folder as verify_cue
from tools.nexium_enemy_attack_cue import expect_cue
from tools.nexium_attack_preview_hud import _final_aim
from tools.nexium_duel_victory import _sample
from tools.nexium_selected_unit_hud import DIGITS,WHITE,DARK,HELP
from tools.nexium_visual_digest import similar

GOLD=(251,220,90)
# The native SDL glyph positions: DMG 6 at x1090, y675; 2 at same x.
# Guard sample of 'D' is white only when a forecast is actually displayed.
PANEL={"label":(1091,676),"ko":(1189,676)}
DIGIT_X=1122

def _check(image,expected):
    read=_sample(image,PANEL)
    for key,want in expected.items():
        if not similar(read[key],want):
            raise ValueError("target damage HUD pixel mismatch "+key+
                             " expected="+str(want)+" observed="+str(read[key]))
    return True

def _digits(image,number):
    if not (0<number<=99):
        raise ValueError("invalid displayed damage")
    expected={}
    for i,digit in enumerate(str(number)):
        for y,mask in enumerate(DIGITS[digit]):
            for x in range(3):
                expected[f"{i}-{x}-{y}"]=bool(mask & (1 << (2-x)))
    best=0
    # Bounded registration only; every one of 15/30 bitmap bits must agree.
    for ox in (-1,0,1):
        for oy in (-3,-2,-1,0):
            pos={}
            for key in expected:
                i,x,y=(int(n) for n in key.split("-"))
                pos[key]=(DIGIT_X+8*i+2*x+1+ox,675+2*y+1+oy)
            got=_sample(image,pos)
            score=sum(similar(got[k],WHITE if lit else DARK)
                      for k,lit in expected.items())
            best=max(best,score)
            if score==len(expected):return True
    raise ValueError("target damage numeral mismatch "+str(number)+
                     " bits="+str(best)+"/"+str(len(expected)))

def expect_visible(image,damage,*,lethal=False):
    _check(image,{"label":WHITE,"ko":GOLD if lethal else DARK})
    _digits(image,damage)
    return True

def expect_hidden(image,*,enemy_visible):
    color=DARK if enemy_visible else HELP
    return _check(image,{"label":color,"ko":color})

def verify_folder(duel,defeat):
    # Independently re-check old Stage44/50/52/54/55/56/57 evidence first.
    verify_cue(duel,defeat)
    with Image.open(duel/"nexium-window.png") as initial, \
         Image.open(_final_aim(duel,"action-duel-aim-")) as first_aim, \
         Image.open(duel/"action-duel-attacked.png") as first_hit, \
         Image.open(_final_aim(duel,"action-victory-round4-aim-nav-")) as last_aim, \
         Image.open(duel/"action-victory-round4-attacked.png") as won, \
         Image.open(defeat/"action-defeat-round-8.png") as lost:
        # verify_cue already authenticated all full-state hashes and cursor
        # positions. This checker deliberately relies on actual PNG pixels.
        expect_hidden(initial,enemy_visible=False)
        expect_visible(first_aim,6,lethal=False)
        expect_hidden(first_hit,enemy_visible=True)
        expect_visible(last_aim,2,lethal=True)
        expect_hidden(won,enemy_visible=False)
        expect_hidden(lost,enemy_visible=False)
    return True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duel",type=Path,required=True)
    parser.add_argument("--defeat",type=Path,required=True)
    args=parser.parse_args()
    verify_folder(args.duel,args.defeat)
    print("VH_TARGET_DAMAGE verified=true first_hit=6 final_hit=2 lethal_KO=true hidden_spent_terminal=true")

if __name__=="__main__":main()
