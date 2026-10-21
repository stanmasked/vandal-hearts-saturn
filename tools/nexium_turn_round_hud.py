#!/usr/bin/env python3
"""Stage61: audit displayed ROUND text in actual registered NeXium screenshots."""
from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image

from tools.nexium_target_health_bar import verify_folder as verify_health_bar
from tools.nexium_attack_preview_hud import _final_aim
from tools.nexium_second_round import _receipt
from tools.nexium_duel_victory import _sample
from tools.nexium_selected_unit_hud import DIGITS, WHITE, DARK, HELP
from tools.nexium_visual_digest import similar

R = (6,5,6,5,5)
BOX = {"background":(94,678)}

def _bitmap(image,round_number):
    if not (1<=round_number<=99):raise ValueError("round counter out of display range")
    expected={}
    for letter,start_x,masks in (
        ("r",97,R),
        *[(str(i),113+8*i,DIGITS[d])
          for i,d in enumerate(str(round_number))],
    ):
        for y,mask in enumerate(masks):
            for x in range(3):
                expected[f"{letter}-{start_x}-{x}-{y}"]=bool(mask & (1 << (2-x)))
    best=0
    # Accept only calibration rounding +/-1 x, -3..0 y; all R/digit
    # white AND dark bitmap bits must agree in a single transform.
    for dx in (-1,0,1):
        for dy in (-3,-2,-1,0):
            samples={}
            for key in expected:
                _,xpos,x,y=key.split("-")
                samples[key]=(int(xpos)+2*int(x)+1+dx,681+2*int(y)+1+dy)
            measured=_sample(image,samples)
            hits=sum(similar(measured[k],WHITE if on else DARK)
                     for k,on in expected.items())
            best=max(best,hits)
            if hits==len(expected):return True
    raise ValueError("round HUD numeral mismatch R "+str(round_number)+
                     " bitmap="+str(best)+"/"+str(len(expected)))

def expect_round(image,n):
    p=_sample(image,BOX)
    if not similar(p["background"],DARK):
        raise ValueError("round HUD background expected dark, got "+str(p))
    return _bitmap(image,n)

def expect_hidden(image):
    points={"a":(94,678),"b":(98,685),"c":(116,689),"d":(134,696)}
    got=_sample(image,points)
    if any(not similar(p,HELP) for p in got.values()):
        raise ValueError("ghost round HUD visible during terminal phase")
    return True

def verify_folder(duel,defeat):
    # Re-open each Stage44-60 guest-verified image and only then audit badge.
    verify_health_bar(duel,defeat)
    round2=_receipt(duel,"round2-evidence.json")
    ended=round2["ended_proof"]
    if ended not in ("action-round2-ended.png","action-round2-ended-retry.png"):
        raise ValueError("untrusted round2 cursor screenshot")
    with Image.open(duel/"nexium-window.png") as initial, \
         Image.open(_final_aim(duel,"action-duel-aim-")) as aim, \
         Image.open(duel/"action-duel-attacked.png") as hit, \
         Image.open(duel/ended) as round2_frame, \
         Image.open(_final_aim(duel,"action-victory-round4-aim-nav-")) as round4_frame, \
         Image.open(duel/"action-victory-round4-attacked.png") as win, \
         Image.open(defeat/"action-defeat-round-8.png") as loss:
        for frame in (initial,aim,hit):expect_round(frame,1)
        expect_round(round2_frame,2)
        expect_round(round4_frame,4)
        expect_hidden(win)
        expect_hidden(loss)
    return True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duel",type=Path,required=True)
    parser.add_argument("--defeat",type=Path,required=True)
    options=parser.parse_args()
    verify_folder(options.duel,options.defeat)
    print("VH_ROUND_HUD verified=true round1_before_after_strike=true round2=true round4=true hidden_terminal=true")

if __name__=="__main__":
    main()
