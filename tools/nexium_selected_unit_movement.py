#!/usr/bin/env python3
"""Stage62: verify MOV allowance on real selected-ally NeXium PNGs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image

from tools.nexium_selected_unit_hud import verify_folder as verify_selected
from tools.nexium_selected_unit_hud import _sample, WHITE, DARK, HELP
from tools.nexium_visual_digest import similar

GLYPHS = {
    "M": (5,7,7,5,5), "O": (2,5,5,5,2), "V": (5,5,5,5,2),
    "0": (7,5,5,5,7), "1": (2,6,2,2,7), "2": (7,1,7,4,7),
    "3": (7,1,7,1,7), "4": (5,5,7,1,1), "5": (7,4,7,1,7),
    "6": (7,4,7,5,7), "7": (7,1,1,1,1), "8": (7,5,7,5,7),
    "9": (7,5,7,1,7),
}
# The glyph begins at logical x=540; sampling uses +1 for the cell's
# registered point, so the probe origin is x=539 (as with the HP digit gate).
X,Y=539,683

def _expected(text):
    bits={}
    for i,char in enumerate(text):
        glyph=GLYPHS.get(char,(0,0,0,0,0))
        for y,mask in enumerate(glyph):
            for x in range(3):
                bits[f"{i}-{x}-{y}"]=bool(mask & (1 << (2-x)))
    return bits

def expect_movement(image,points):
    if not isinstance(points,int) or points<0 or points>9:
        raise ValueError("unsupported MOV allowance")
    bits=_expected("MOV "+str(points))
    for offset_y in (-3,-2,-1,0):
        positions={
            key:(X+8*int(key.split("-")[0])+2*int(key.split("-")[1])+1,
                 Y+2*int(key.split("-")[2])+1+offset_y)
            for key in bits
        }
        observed=_sample(image,positions)
        if all(similar(observed[k],WHITE if lit else DARK) for k,lit in bits.items()):
            return True
    raise ValueError("MOV allowance bitmap mismatch expected="+str(points))

def expect_hidden(image):
    points={
        f"{i}-{x}-{y}":(X+8*i+2*x+1,Y+2*y+1)
        for i in range(5) for x in range(3) for y in range(5)
    }
    observed=_sample(image,points)
    if any(not similar(pixel,HELP) for pixel in observed.values()):
        raise ValueError("ghost MOV stat visible without selected ally")
    return True

def verify_folder(duel,defeat):
    # Existing Stage55 checks real selected marker, HP, action readiness,
    # battle hashes, and hide/show states first.
    verify_selected(duel,defeat)
    attack=json.loads((duel/"attack-evidence.json").read_text("utf8"))
    round2=json.loads((duel/"round2-evidence.json").read_text("utf8"))
    victory=json.loads((duel/"victory-evidence.json").read_text("utf8"))
    selected=attack.get("selected_proof")
    round2_selected=round2.get("selection_proof")
    fourth=victory.get("round4_selection_proof")
    allowed=("action-duel-selected.png","action-duel-selected-retry.png")
    if selected not in allowed:raise ValueError("invalid selected evidence")
    if round2_selected not in ("action-round2-selected.png","action-round2-selected-retry.png"):
        raise ValueError("invalid round2 selection evidence")
    if fourth not in ("action-victory-round4-selected.png","action-victory-round4-selected-retry.png"):
        raise ValueError("invalid round4 selection evidence")
    with Image.open(duel/"nexium-window.png") as initial, \
         Image.open(duel/selected) as first, \
         Image.open(duel/"action-duel-attacked.png") as attacked, \
         Image.open(duel/round2_selected) as second, \
         Image.open(duel/fourth) as fourth_round, \
         Image.open(duel/"action-victory-round4-attacked.png") as won, \
         Image.open(defeat/"action-defeat-round-8.png") as lost:
        expect_hidden(initial)
        for frame in (first,attacked,second,fourth_round):
            expect_movement(frame,4)
        expect_hidden(won)
        expect_hidden(lost)
    return True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duel",type=Path,required=True)
    parser.add_argument("--defeat",type=Path,required=True)
    args=parser.parse_args()
    verify_folder(args.duel,args.defeat)
    print("VH_SELECTED_MOV verified=true scout=4 hidden_no_selection_terminal=true")

if __name__=="__main__":main()
