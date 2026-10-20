#!/usr/bin/env python3
"""Stage48: prove actual enemy retaliation and a fresh player-round attack.

This is a continuation of the already screenshot-verified ROM-free duel.
Require matching 64-bit guest state, both unit HP bars and action receipts.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
from PIL import Image
from tools.nexium_attack_action import ATTACKED_DUEL
from tools.nexium_duel_reselect import verify_folder as verify_reselect
from tools.nexium_post_move import _effect
from tools.nexium_tactical_action import RealX11, _center, _near, _require_state, _selected_marker
from tools.nexium_visual_digest import (
    ANCHORS, ANCHOR_SIZE, _calibration, _magenta_components, similar,
)

ROUND2 = "b633fd92746c41cf"
ROUND2_ATTACK = "203a8823191e6018"
GREEN = (117, 221, 109)
DARK = (31, 32, 32)


def _read_hp_pixels(image):
    rgb = image.convert("RGB")
    calibration = _calibration(_magenta_components(rgb))
    if calibration is None:
        raise ValueError("HP bar screenshot registration is missing")
    origin, sx, sy = calibration
    ax = ANCHORS[0][0] + (ANCHOR_SIZE-1)/2
    ay = ANCHORS[0][1] + (ANCHOR_SIZE-1)/2
    def pixel(x, y):
        px = round(origin[0]+(x-ax)*sx)
        py = round(origin[1]+(y-ay)*sy)
        if not (0 <= px < rgb.width and 0 <= py < rgb.height):
            raise ValueError("HP bar pixel outside screenshot")
        return rgb.getpixel((px,py))
    # Scout at {1,5}: hp rect x463..496, y195..199; 22HP=28px,
    # 19HP=24px. Raider at {2,5}: rect x503..536, y215..219;
    # 14HP=18px, 8HP=10px. Sample only uncontested interior pixels.
    return {
        "scout_stable": pixel(475,197),
        "scout_lost": pixel(489,197),
        "raider_stable": pixel(508,217),
        "raider_lost": pixel(517,217),
    }


def _hp(image, scout, raider):
    if (scout,raider) not in ((22,14),(19,14),(19,8)):
        raise ValueError("unsupported combat HP checkpoint")
    colors = _read_hp_pixels(image)
    expected = {
        "scout_stable": GREEN,
        "scout_lost": GREEN if scout == 22 else DARK,
        "raider_stable": GREEN,
        "raider_lost": GREEN if raider == 14 else DARK,
    }
    for part, value in expected.items():
        if not similar(colors[part],value):
            raise ValueError("HP pixel mismatch for "+part+
                             " expected "+str(value)+" observed "+str(colors[part]))
    return True


def _navigate(io, initial, goal, scout, label, record):
    cursor=initial
    for i in range(1,13):
        if _near(cursor,goal):
            return
        if abs(cursor[1]-goal[1])>80:
            raise ValueError("new-round cursor went off duel row")
        key="Right" if cursor[0]<goal[0] else "Left"
        image=io.capture_after(key,f"round2-{label}-{i}")
        _require_state(image,ROUND2)
        _hp(image,19,14)
        nxt=_center(image)
        stalled=_near(nxt,cursor)
        record.append({"key":key,"phase":label,"cursor_x":round(nxt[0],2),
                       "stalled":stalled})
        if stalled:
            io.focus()
        cursor=nxt
    if not _near(cursor,goal):
        raise ValueError("new-round cursor did not reach selected tile in 12 observations")


def exercise(initial, prior, io):
    _require_state(initial,"9376e23745926630")
    _require_state(prior,ATTACKED_DUEL)
    _effect(prior,"Rejected")
    _hp(prior,22,14)
    scout=_center(initial)
    raider=_center(prior)
    if not _selected_marker(prior,scout):
        raise ValueError("Scout must still be selected before end turn")
    if raider[0] <= scout[0]+12:
        raise ValueError("Raider cursor not at east adjacent tile")
    steps=[]
    ended=io.capture_after("x","round2-ended")
    end_file="action-round2-ended.png"
    try:
        _require_state(ended,ROUND2)
    except ValueError:
        # Retry only the unchanged previous state; never replay EndTurn
        # after an unexpected state transition or partial combat mutation.
        _require_state(ended,ATTACKED_DUEL)
        io.focus()
        ended=io.capture_after("x","round2-ended-retry")
        _require_state(ended,ROUND2)
        end_file="action-round2-ended-retry.png"
    _effect(ended,"TurnEnded")
    _hp(ended,19,14)
    if _selected_marker(ended,scout):
        raise ValueError("Scout remained selected after round ended")
    if not _near(_center(ended),raider):
        raise ValueError("end turn moved cursor")
    steps.append({"key":"x","effect":"TurnEnded","round":2,
                  "scout_hp":19,"raider_hp":14})

    no_select=io.capture_after("y","round2-no-select")
    _require_state(no_select,ROUND2)
    _effect(no_select,"Rejected")
    _hp(no_select,19,14)
    if _selected_marker(no_select,scout):
        raise ValueError("unselected Scout gained an outline")
    steps.append({"key":"y","effect":"Rejected","reason":"no_selection"})

    _navigate(io,_center(no_select),scout,scout,"return",steps)
    selected=io.capture_after("Return","round2-selected")
    selected_file="action-round2-selected.png"
    _require_state(selected,ROUND2)
    _hp(selected,19,14)
    if not _selected_marker(selected,scout):
        io.focus()
        selected=io.capture_after("space","round2-selected-retry")
        selected_file="action-round2-selected-retry.png"
        _require_state(selected,ROUND2)
        _hp(selected,19,14)
    _effect(selected,"Selected")
    if not _selected_marker(selected,scout):
        raise ValueError("Scout outline missing in second round")
    if not _near(_center(selected),scout):
        raise ValueError("second round selected wrong unit")
    steps.append({"key":"Return/space","effect":"Selected","round":2})

    _navigate(io,scout,raider,scout,"aim",steps)
    hit=io.capture_after("y","round2-attacked")
    _require_state(hit,ROUND2_ATTACK)
    _effect(hit,"Attacked")
    _hp(hit,19,8)
    if not _selected_marker(hit,scout) or not _near(_center(hit),raider):
        raise ValueError("second round attack lost Scout aim or selection")
    steps.append({"key":"y","effect":"Attacked","round":2,"raider_hp":8})
    again=io.capture_after("y","round2-rejected")
    _require_state(again,ROUND2_ATTACK)
    _effect(again,"Rejected")
    _hp(again,19,8)
    if not _selected_marker(again,scout):
        raise ValueError("second round rejection lost Scout selection")
    steps.append({"key":"y","effect":"Rejected","round":2,"raider_hp":8})
    return {
        "format":"VHS48-ROM-free-second-round-v1",
        "second_round_passed":True,
        "round2_fingerprint":ROUND2,
        "round2_attack_fingerprint":ROUND2_ATTACK,
        "scout_hp_before":22,"scout_hp_after":19,
        "raider_hp_before":14,"raider_hp_after":8,
        "second_round_repeated_attack_rejected":True,
        "ended_proof":end_file,
        "no_selection_proof":"action-round2-no-select.png",
        "selection_proof":selected_file,
        "attack_proof":"action-round2-attacked.png",
        "rejection_proof":"action-round2-rejected.png",
        "steps":steps,
        "scope":"ROM-free shared native tactical prototype, not Sega Saturn game footage",
    }


def verify_folder(folder):
    verify_reselect(folder)
    report=json.loads((folder/"round2-evidence.json").read_text("utf-8"))
    for key, value in {
        "format":"VHS48-ROM-free-second-round-v1",
        "second_round_passed":True,
        "round2_fingerprint":ROUND2,
        "round2_attack_fingerprint":ROUND2_ATTACK,
        "scout_hp_before":22,"scout_hp_after":19,
        "raider_hp_before":14,"raider_hp_after":8,
        "second_round_repeated_attack_rejected":True,
        "no_selection_proof":"action-round2-no-select.png",
        "attack_proof":"action-round2-attacked.png",
        "rejection_proof":"action-round2-rejected.png",
    }.items():
        if report.get(key)!=value:
            raise ValueError("second-round receipt mismatch: "+key)
    ended=report.get("ended_proof")
    selected=report.get("selection_proof")
    if ended not in ("action-round2-ended.png","action-round2-ended-retry.png"):
        raise ValueError("unexpected end-turn frame filename")
    if selected not in ("action-round2-selected.png","action-round2-selected-retry.png"):
        raise ValueError("unexpected round-two selection filename")
    with Image.open(folder/"nexium-window.png") as initial, \
         Image.open(folder/"action-reselect-rejected.png") as prior, \
         Image.open(folder/ended) as end, \
         Image.open(folder/"action-round2-no-select.png") as unselected, \
         Image.open(folder/selected) as selection, \
         Image.open(folder/"action-round2-attacked.png") as attacked, \
         Image.open(folder/"action-round2-rejected.png") as rejected:
        scout=_center(initial)
        raider=_center(prior)
        _require_state(prior,ATTACKED_DUEL)
        _hp(prior,22,14)
        for frame in (end,unselected,selection):
            _require_state(frame,ROUND2)
            _hp(frame,19,14)
        for frame in (attacked,rejected):
            _require_state(frame,ROUND2_ATTACK)
            _hp(frame,19,8)
        for frame,effect in ((end,"TurnEnded"),(unselected,"Rejected"),
                             (selection,"Selected"),(attacked,"Attacked"),(rejected,"Rejected")):
            _effect(frame,effect)
        if _selected_marker(end,scout) or _selected_marker(unselected,scout):
            raise ValueError("selection leaked across end turn")
        for frame in (selection,attacked,rejected):
            if not _selected_marker(frame,scout):
                raise ValueError("selection outline not visible after round reset")
        if not _near(_center(end),raider) or not _near(_center(unselected),raider):
            raise ValueError("end/no-selection cursor moved")
        if not _near(_center(selection),scout):
            raise ValueError("second-round selection aimed at wrong tile")
        if not _near(_center(attacked),raider) or not _near(_center(rejected),raider):
            raise ValueError("second-round attack aimed at wrong tile")
    return True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window")
    parser.add_argument("--folder",type=Path,default=Path("runtime-evidence"))
    parser.add_argument("--verify-dir",type=Path)
    opts=parser.parse_args()
    if opts.verify_dir is not None:
        verify_folder(opts.verify_dir)
        print("VH_ROUND2 verified=true scout=22->19 raider=14->8 repeated=false")
        return
    if not opts.window:
        parser.error("live round-two proof requires --window")
    opts.folder.mkdir(parents=True,exist_ok=True)
    try:
        with Image.open(opts.folder/"nexium-window.png") as initial, \
             Image.open(opts.folder/"action-reselect-rejected.png") as previous:
            report=exercise(initial.convert("RGB"),previous.convert("RGB"),
                            RealX11(opts.window,opts.folder))
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        report={"format":"VHS48-ROM-free-second-round-v1",
                "second_round_passed":False,"error_type":type(error).__name__,
                "error":str(error)}
    (opts.folder/"round2-evidence.json").write_text(
        json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    if not report["second_round_passed"]:
        raise SystemExit("Stage48 NeXium second-round result not verified")


if __name__=="__main__":
    main()
