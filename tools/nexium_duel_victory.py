#!/usr/bin/env python3
"""Stage50: prove four-round ROM-free duel VICTORY from real NeXium screenshots.

Runs ONLY after Stage48 actual second-round hit and rejection passed. Every
accepted transition needs a canonical on-screen fingerprint, registered unit
HP pixels, selected-unit outline and an action receipt. Host JSON is not proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from PIL import Image

from tools.nexium_second_round import (
    ROUND2_ATTACK, _hp as _round2_hp, _round_end_receipt,
    verify_folder as verify_round2,
)
from tools.nexium_tactical_action import (
    RealX11, _center, _near, _require_state, _selected_marker,
)
from tools.nexium_post_move import _effect
from tools.nexium_visual_digest import (
    ANCHORS, ANCHOR_SIZE, _calibration, _magenta_components, similar,
)

ROUND3 = "1b81f3931a165925"      # Scout HP 16 / Raider HP 8
ROUND3_ATTACK = "7849484ccfd7a0de"  # Scout HP 16 / Raider HP 2
ROUND4 = "984023d699c803db"      # Scout HP 13 / Raider HP 2
VICTORY = "6097117b6c951fb6"     # Scout HP 13 / Raider HP 0
GREEN = (117, 221, 109)
RED = (239, 79, 76)


def _sample(image, positions):
    rgb = image.convert("RGB")
    calibration = _calibration(_magenta_components(rgb))
    if calibration is None:
        raise ValueError("missing registered HP and sprite anchor geometry")
    origin, sx, sy = calibration
    ax = ANCHORS[0][0] + (ANCHOR_SIZE - 1) / 2
    ay = ANCHORS[0][1] + (ANCHOR_SIZE - 1) / 2
    result = {}
    for name, (x, y) in positions.items():
        px = round(origin[0] + (x - ax) * sx)
        py = round(origin[1] + (y - ay) * sy)
        if not (0 <= px < rgb.width and 0 <= py < rgb.height):
            raise ValueError("registered sample outside actual guest frame")
        result[name] = rgb.getpixel((px, py))
    return result


def _hp(image, scout_hp, raider_hp):
    if (scout_hp, raider_hp) not in ((16, 8), (16, 2), (13, 2), (13, 0)):
        raise ValueError("unexpected victory duel HP checkpoint")
    # Real Stage48 guest 1279x700 screenshot supplies calibration; sample
    # x482 separates Scout HP16 from HP13. Raider x504 is still green
    # with 2HP (two logical pixels), while x513 separates 8HP from 2HP.
    colors = _sample(image, {
        "scout_base": (473, 197),
        "scout_13_or_16": (482, 197),
        "scout_not_19": (489, 197),
        "raider_base": (504, 217),
        "raider_8": (513, 217),
        "enemy_body": (520, 245),
    })
    expectation = {
        "scout_base": True,
        "scout_13_or_16": scout_hp == 16,
        "scout_not_19": False,
        "raider_base": raider_hp > 0,
        "raider_8": raider_hp == 8,
    }
    for name, should_be_green in expectation.items():
        observed = similar(colors[name], GREEN)
        if observed != should_be_green:
            raise ValueError("registered HP pixel mismatch: " + name +
                             " observed=" + str(colors[name]) +
                             " scout=" + str(scout_hp) +
                             " raider=" + str(raider_hp))
    if raider_hp == 0 and similar(colors["enemy_body"], RED):
        raise ValueError("defeated Raider still visibly present")
    return True


def _end_round(io, label, old_hash, new_hash, scout_hp, raider_hp, scout, raider, steps):
    end = io.capture_after("x", label)
    chosen = "action-" + label + ".png"
    try:
        _require_state(end, new_hash)
    except ValueError:
        # Retry only if precisely the *unchanged* canonical previous round.
        _require_state(end, old_hash)
        io.focus()
        end = io.capture_after("x", label + "-retry")
        chosen = "action-" + label + "-retry.png"
        _require_state(end, new_hash)
    _hp(end, scout_hp, raider_hp)
    if _selected_marker(end, scout):
        raise ValueError("ending a turn did not clear Scout selection")
    if not _near(_center(end), raider):
        raise ValueError("end turn unexpectedly moved cursor")
    effect = _round_end_receipt(end)
    steps.append({"key": "x", "checkpoint": label, "effect": effect,
                  "scout_hp": scout_hp, "raider_hp": raider_hp})
    return chosen, end


def _navigate(io, start, destination, state, scout_hp, raider_hp, label, steps):
    current = start
    for attempt in range(1, 13):
        if _near(current, destination):
            return current
        if abs(current[1] - destination[1]) > 80:
            raise ValueError(label + " cursor escaped expected map row")
        key = "Left" if current[0] > destination[0] else "Right"
        frame = io.capture_after(key, label + "-nav-" + str(attempt))
        _require_state(frame, state)
        _hp(frame, scout_hp, raider_hp)
        nxt = _center(frame)
        stalled = _near(nxt, current)
        steps.append({"key": key, "checkpoint": label, "stalled": stalled,
                      "x": round(nxt[0], 2)})
        if stalled:
            io.focus()
        current = nxt
    if not _near(current, destination):
        raise ValueError(label + " cursor failed after twelve observed pulses")
    return current


def _attack_new_round(io, scout, raider, base_hash, hit_hash, scout_hp,
                      before_raider_hp, after_raider_hp, prefix, steps):
    _navigate(io, raider, scout, base_hash, scout_hp, before_raider_hp,
              prefix + "-return", steps)
    selected = io.capture_after("Return", prefix + "-selected")
    selected_name = "action-" + prefix + "-selected.png"
    _require_state(selected, base_hash)
    _hp(selected, scout_hp, before_raider_hp)
    if not _selected_marker(selected, scout):
        io.focus()
        selected = io.capture_after("space", prefix + "-selected-retry")
        selected_name = "action-" + prefix + "-selected-retry.png"
        _require_state(selected, base_hash)
        _hp(selected, scout_hp, before_raider_hp)
    _effect(selected, "Selected")
    if not _selected_marker(selected, scout) or not _near(_center(selected), scout):
        raise ValueError(prefix + " Scout not visually selected")
    _navigate(io, scout, raider, base_hash, scout_hp, before_raider_hp,
              prefix + "-aim", steps)
    attacked = io.capture_after("y", prefix + "-attacked")
    _require_state(attacked, hit_hash)
    _effect(attacked, "Attacked")
    _hp(attacked, scout_hp, after_raider_hp)
    if not _selected_marker(attacked, scout) or not _near(_center(attacked), raider):
        raise ValueError(prefix + " attack lost selection or target")
    steps.append({"key": "y", "checkpoint": prefix,
                  "effect": "Attacked", "raider_hp": after_raider_hp})
    return selected_name, attacked


def exercise(initial, previous, io):
    _require_state(initial, "9376e23745926630")
    _require_state(previous, ROUND2_ATTACK)
    _round2_hp(previous, 19, 8)
    _effect(previous, "Rejected")
    scout, raider = _center(initial), _center(previous)
    if not _selected_marker(previous, scout):
        raise ValueError("Stage48 ended without visibly selected Scout")
    steps = []

    third_end, _ = _end_round(io, "victory-round3-ended", ROUND2_ATTACK,
                            ROUND3, 16, 8, scout, raider, steps)
    third_selection, _ = _attack_new_round(
        io, scout, raider, ROUND3, ROUND3_ATTACK, 16, 8, 2, "victory-round3", steps)
    rejected = io.capture_after("y", "victory-round3-rejected")
    _require_state(rejected, ROUND3_ATTACK)
    _effect(rejected, "Rejected")
    _hp(rejected, 16, 2)
    if not _selected_marker(rejected, scout):
        raise ValueError("third-round repeat lost selected Scout")

    fourth_end, _ = _end_round(io, "victory-round4-ended", ROUND3_ATTACK,
                             ROUND4, 13, 2, scout, raider, steps)
    fourth_selection, _ = _attack_new_round(
        io, scout, raider, ROUND4, VICTORY, 13, 2, 0, "victory-round4", steps)
    for key, name in (("x", "post-victory-end-turn"),
                      ("y", "post-victory-attack")):
        frame = io.capture_after(key, name)
        _require_state(frame, VICTORY)
        _effect(frame, "Rejected")
        _hp(frame, 13, 0)
        if not _selected_marker(frame, scout) or not _near(_center(frame), raider):
            raise ValueError("victory terminal rejection lost cursor/selection")
        steps.append({"key": key, "checkpoint": name, "effect": "Rejected"})
    return {
        "format": "VHS50-ROM-free-victory-v1",
        "victory_passed": True,
        "round3_hash": ROUND3, "round3_attack_hash": ROUND3_ATTACK,
        "round4_hash": ROUND4, "victory_hash": VICTORY,
        "scout_hp_after": 13, "raider_hp_after": 0,
        "terminal_turn_and_attack_rejected": True,
        "round3_end_proof": third_end,
        "round3_selection_proof": third_selection,
        "round3_attack_proof": "action-victory-round3-attacked.png",
        "round3_reject_proof": "action-victory-round3-rejected.png",
        "round4_end_proof": fourth_end,
        "round4_selection_proof": fourth_selection,
        "victory_attack_proof": "action-victory-round4-attacked.png",
        "post_victory_end_proof": "action-post-victory-end-turn.png",
        "post_victory_attack_proof": "action-post-victory-attack.png",
        "steps": steps,
        "scope": "ROM-free native homebrew tactics, not original Saturn combat",
    }


def _allowed(report, field, possibilities):
    name = report.get(field)
    if name not in possibilities:
        raise ValueError("untrusted victory evidence filename: " + field)
    return name


def verify_folder(folder):
    verify_round2(folder)
    report = json.loads((folder / "victory-evidence.json").read_text("utf-8"))
    expected = {"format": "VHS50-ROM-free-victory-v1",
                "victory_passed": True,
                "round3_hash": ROUND3,
                "round3_attack_hash": ROUND3_ATTACK,
                "round4_hash": ROUND4,
                "victory_hash": VICTORY,
                "scout_hp_after": 13, "raider_hp_after": 0,
                "terminal_turn_and_attack_rejected": True}
    for field, value in expected.items():
        if report.get(field) != value:
            raise ValueError("victory receipt missing: " + field)
    checked = [
        ("round3_end_proof", "victory-round3-ended", ROUND3, 16, 8,
         None, False),
        ("round3_selection_proof", "victory-round3-selected", ROUND3, 16, 8,
         "Selected", True),
        ("round3_attack_proof", "victory-round3-attacked", ROUND3_ATTACK, 16, 2,
         "Attacked", True),
        ("round3_reject_proof", "victory-round3-rejected", ROUND3_ATTACK, 16, 2,
         "Rejected", True),
        ("round4_end_proof", "victory-round4-ended", ROUND4, 13, 2,
         None, False),
        ("round4_selection_proof", "victory-round4-selected", ROUND4, 13, 2,
         "Selected", True),
        ("victory_attack_proof", "victory-round4-attacked", VICTORY, 13, 0,
         "Attacked", True),
        ("post_victory_end_proof", "post-victory-end-turn", VICTORY, 13, 0,
         "Rejected", True),
        ("post_victory_attack_proof", "post-victory-attack", VICTORY, 13, 0,
         "Rejected", True),
    ]
    with Image.open(folder / "nexium-window.png") as start, \
         Image.open(folder / "action-round2-rejected.png") as previous:
        scout, raider = _center(start), _center(previous)
        _require_state(previous, ROUND2_ATTACK)
        _round2_hp(previous, 19, 8)
        for field, basename, state, hp1, hp2, effect, selected in checked:
            names = ["action-" + basename + ".png"]
            if field in ("round3_end_proof", "round4_end_proof",
                         "round3_selection_proof", "round4_selection_proof"):
                names.append("action-" + basename + "-retry.png")
            name = _allowed(report, field, names)
            with Image.open(folder / name) as image:
                _require_state(image, state)
                _hp(image, hp1, hp2)
                if effect is None:
                    _round_end_receipt(image)
                else:
                    _effect(image, effect)
                if bool(_selected_marker(image, scout)) != selected:
                    raise ValueError("victory selected-outline mismatch: " + field)
                target = scout if "selection" in field else raider
                if not _near(_center(image), target):
                    raise ValueError("victory cursor/target mismatch: " + field)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window")
    parser.add_argument("--folder", type=Path, default=Path("runtime-evidence"))
    parser.add_argument("--verify-dir", type=Path)
    options = parser.parse_args()
    if options.verify_dir:
        verify_folder(options.verify_dir)
        print("VH_VICTORY verified=true round=4 scout_hp=13 raider_hp=0 terminal=true")
        return
    if not options.window:
        parser.error("live Stage50 needs a real NeXium X11 window")
    options.folder.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(options.folder / "nexium-window.png") as start, \
             Image.open(options.folder / "action-round2-rejected.png") as previous:
            result = exercise(start.convert("RGB"), previous.convert("RGB"),
                              RealX11(options.window, options.folder))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        result = {"format": "VHS50-ROM-free-victory-v1", "victory_passed": False,
                  "error_type": type(error).__name__, "error": str(error)}
    (options.folder / "victory-evidence.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["victory_passed"] is not True:
        raise SystemExit("Stage50 guest victory unverified")


if __name__ == "__main__":
    main()
