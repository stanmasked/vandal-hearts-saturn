#!/usr/bin/env python3
"""Stage52: real ROM-free guest Defeat after eight unopposed Raider strikes.

Separate NeXium session, separate from verified Stage50 Victory. No claimed
outcome is accepted without a full 64-bit guest framebuffer state signature,
registered HP/sprite pixels, end-turn action receipt and terminal rejections.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
from PIL import Image

from tools.nexium_attack_action import INITIAL_DUEL
from tools.nexium_duel_victory import _sample
from tools.nexium_post_move import _effect
from tools.nexium_second_round import _round_end_receipt
from tools.nexium_tactical_action import (
    RealX11, _center, _near, _require_state, _selected_marker,
)
from tools.nexium_visual_digest import similar

# Native C++ StateDigest over the entire Battle (including rounds, phase,
# original unit stats and acted/moved flags), not an independently editable log.
ROUND_HASHES = (
    "9376e23745926630",  # initial round 1, Scout HP22
    "cbda1f619741fbf5",  # round 2, HP19
    "63612b72203eb079",  # round 3, HP16
    "66070dc6b67566ad",  # round 4, HP13
    "cdeb89c69e09b7e9",  # round 5, HP10
    "413b700b4a1466e5",  # round 6, HP7
    "a6cd3306a9d5b5e1",  # round 7, HP4
    "11c830508d90884d",  # round 8, HP1
    "3b0411b006f113c1",  # Defeat in round 8, HP0
)
SCOUT_HP = (22, 19, 16, 13, 10, 7, 4, 1, 0)
GREEN = (117, 221, 109)
DARK = (31, 32, 32)
BLUE = (63, 167, 239)
RED = (239, 79, 76)


def _hp(image, scout_hp):
    if scout_hp not in SCOUT_HP:
        raise ValueError("unsupported Defeat HP checkpoint")
    width = max(1, min(34, scout_hp * 34 // 26))
    coords = {
        "scout_start": (463,197), "scout_near_left": (462,197),
        "scout_blue": (480,230),
        "raider_body": (520,250),
        "raider_green": (515,217), "raider_green_end": (525,217),
        "raider_dark": (532,217),
    }
    if scout_hp > 0:
        coords["scout_inside"] = (463 + (0 if width == 1 else width - 2),197)
        coords["scout_outside"] = (463 + width + 2,197)
    colors = _sample(image, coords)
    if not similar(colors["raider_body"], RED):
        raise ValueError("living Raider red sprite missing")
    for name in ("raider_green", "raider_green_end"):
        if not similar(colors[name], GREEN):
            raise ValueError("Raider 20HP bar changed: " + name)
    if not similar(colors["raider_dark"], DARK):
        raise ValueError("Raider 20HP background shifted")
    if scout_hp == 0:
        # This left-neighbor sample is essential: NeXium scales the 1280px
        # guest to 1279px and the *one-pixel* 1HP sliver lands on logical
        # x462, not x463. The death case must also reject that ghost sliver.
        if (similar(colors["scout_start"], GREEN) or
                similar(colors["scout_near_left"], GREEN)):
            raise ValueError("defeated Scout still has green HP bar")
        if similar(colors["scout_blue"], BLUE):
            raise ValueError("defeated Scout blue pawn still visible")
    else:
        if scout_hp == 1:
            # Real Stage52 run #39517943768 survived seven enemy attacks,
            # but its registered (463,197) was DARK; the sole rendered
            # green pixel is at (462,197) after window scaling. Both
            # positions are accepted ONLY for exactly 1HP, and the 64-bit
            # guest state and depleted-bar boundary are still mandatory.
            if not (similar(colors["scout_start"], GREEN) or
                    similar(colors["scout_near_left"], GREEN)):
                raise ValueError("Scout 1HP pixel missing in scaled frame")
        else:
            for name in ("scout_start", "scout_inside"):
                if not similar(colors[name], GREEN):
                    raise ValueError("Scout HP pixel mismatch: " + name + " hp=" + str(scout_hp))
        if not similar(colors["scout_outside"], DARK):
            raise ValueError("Scout depleted HP pixel mismatch: hp=" + str(scout_hp))
        if not similar(colors["scout_blue"], BLUE):
            raise ValueError("living Scout blue pawn missing")
    return True


def _check(image, round_index, scout, raider, receipt=None):
    _require_state(image, ROUND_HASHES[round_index])
    _hp(image, SCOUT_HP[round_index])
    if _selected_marker(image, scout):
        raise ValueError("unexpected Scout selection at Defeat checkpoint")
    if not _near(_center(image), raider):
        raise ValueError("guest cursor moved during skip-turn Defeat route")
    if receipt == "TurnEnded":
        _round_end_receipt(image)  # cyan normally, red only with exact state+HP
    elif receipt is not None:
        _effect(image, receipt)
    return True


def exercise(initial, after_right, io):
    _require_state(initial, INITIAL_DUEL)
    _require_state(after_right, INITIAL_DUEL)
    scout, raider = _center(initial), _center(after_right)
    if raider[0] <= scout[0] + 12:
        raise ValueError("baseline Right cursor probe not observed")
    _hp(after_right, 22)
    if _selected_marker(after_right, scout):
        raise ValueError("Defeat probe must start unselected")
    files, steps = [], []
    for turn in range(1, 9):
        label = "defeat-round-" + str(turn)
        frame = io.capture_after("x", label)
        filename = "action-" + label + ".png"
        try:
            _require_state(frame, ROUND_HASHES[turn])
        except ValueError:
            # Retry only when the old *entire* game state remained unchanged.
            _require_state(frame, ROUND_HASHES[turn - 1])
            _hp(frame, SCOUT_HP[turn - 1])
            io.focus()
            frame = io.capture_after("x", label + "-retry")
            filename = "action-" + label + "-retry.png"
        _check(frame, turn, scout, raider, receipt="TurnEnded")
        files.append(filename)
        steps.append({"turn": turn, "scout_hp": SCOUT_HP[turn],
                      "phase": "Defeat" if turn == 8 else "Player",
                      "proof": filename, "hash": ROUND_HASHES[turn]})
    blocked = []
    for key, label in (("x", "defeat-post-end"),
                       ("y", "defeat-post-attack"),
                       ("Return", "defeat-post-confirm")):
        frame = io.capture_after(key, label)
        _check(frame, 8, scout, raider, receipt="Rejected")
        blocked.append("action-" + label + ".png")
    return {"format": "VHS52-ROM-free-defeat-v1",
            "defeat_passed": True, "round": 8,
            "scout_hp": 0, "raider_hp": 20,
            "round_hashes": list(ROUND_HASHES),
            "proof_files": files, "post_defeat_proofs": blocked,
            "all_terminal_actions_rejected": True, "steps": steps,
            "scope": "Original ROM-free homebrew, not Sega Saturn game footage"}


def verify_folder(folder):
    data = json.loads((folder / "defeat-evidence.json").read_text("utf-8"))
    expect = {"format": "VHS52-ROM-free-defeat-v1",
              "defeat_passed": True, "round": 8, "scout_hp": 0,
              "raider_hp": 20, "round_hashes": list(ROUND_HASHES),
              "all_terminal_actions_rejected": True}
    for field, value in expect.items():
        if data.get(field) != value:
            raise ValueError("Defeat receipt wrong: " + field)
    proof = data.get("proof_files")
    blocked = data.get("post_defeat_proofs")
    if not isinstance(proof,list) or len(proof) != 8:
        raise ValueError("Defeat checkpoint list incomplete")
    if blocked != ["action-defeat-post-end.png",
                   "action-defeat-post-attack.png",
                   "action-defeat-post-confirm.png"]:
        raise ValueError("post-Defeat proof names invalid")
    with Image.open(folder / "nexium-window.png") as before, \
         Image.open(folder / "nexium-after-right.png") as after:
        _require_state(before, INITIAL_DUEL)
        _require_state(after, INITIAL_DUEL)
        scout,raider = _center(before),_center(after)
        _hp(after,22)
        for turn in range(1,9):
            stem = "action-defeat-round-" + str(turn)
            allowed = {stem + ".png", stem + "-retry.png"}
            name = proof[turn-1]
            if name not in allowed:
                raise ValueError("invalid Defeat round filename " + str(turn))
            with Image.open(folder / name) as image:
                _check(image, turn, scout, raider, receipt="TurnEnded")
        for name in blocked:
            with Image.open(folder / name) as image:
                _check(image, 8, scout, raider, receipt="Rejected")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window")
    parser.add_argument("--folder",type=Path,default=Path("runtime-evidence"))
    parser.add_argument("--verify-dir",type=Path)
    args = parser.parse_args()
    if args.verify_dir is not None:
        verify_folder(args.verify_dir)
        print("VH_DEFEAT verified=true round=8 scout_hp=0 raider_hp=20 terminal=true")
        return
    if not args.window:
        parser.error("live Defeat proof needs a real NeXium X11 window")
    args.folder.mkdir(parents=True,exist_ok=True)
    try:
        with Image.open(args.folder/"nexium-window.png") as before, \
             Image.open(args.folder/"nexium-after-right.png") as after:
            report = exercise(before.convert("RGB"),after.convert("RGB"),
                              RealX11(args.window,args.folder))
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        report = {"format":"VHS52-ROM-free-defeat-v1","defeat_passed":False,
                  "error_type":type(error).__name__,"error":str(error)}
    (args.folder/"defeat-evidence.json").write_text(
        json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    if report.get("defeat_passed") is not True:
        raise SystemExit("Stage52 real guest Defeat not verified")


if __name__ == "__main__":
    main()
