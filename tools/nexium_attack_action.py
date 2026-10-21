#!/usr/bin/env python3
"""Stage44: real ROM-free Scout attack and rejected second attack in NeXium.

A separate duel NRO (Scout at 1,5; Raider at 2,5) exercises the SAME
native Battle/TrainingUi code as the default NRO, without Saturn assets.
Only screenshots from the guest are authoritative.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
from PIL import Image
from tools.nexium_tactical_action import (
    RealX11, _center, _near, _require_state, _selected_marker
)
from tools.nexium_post_move import _effect
from tools.nexium_visual_digest import (
    _calibration, _magenta_components, ANCHORS, ANCHOR_SIZE, similar, decode
)

INITIAL_DUEL = "9376e23745926630"
ATTACKED_DUEL = "9a0233cdc1acffdb"
ENEMY_TILE = (2, 5)
GREEN = (117, 221, 109)
DARK = (31, 32, 32)


def _hp_samples(image):
    """Read actual displayed HP bar, not game logs or synthetic receipt."""
    rgb = image.convert("RGB")
    calibrated = _calibration(_magenta_components(rgb))
    if calibrated is None:
        raise ValueError("no visual registration for enemy HP bar")
    anchor, sx, sy = calibrated
    source_x = ANCHORS[0][0] + (ANCHOR_SIZE - 1) / 2
    source_y = ANCHORS[0][1] + (ANCHOR_SIZE - 1) / 2
    # project_training_tile({2,5}) = (520,276); HP bar y = 215..219.
    def sample(x, y):
        px = round(anchor[0] + (x - source_x) * sx)
        py = round(anchor[1] + (y - source_y) * sy)
        if not (0 <= px < rgb.width and 0 <= py < rgb.height):
            raise ValueError("HP sample outside registered screenshot")
        return rgb.getpixel((px, py))
    # At HP20, 26/34 pixels fill; at HP14, 18/34 fill.
    return {"stable": sample(515, 217), "difference": sample(525, 217)}


def _require_hp(image, expected):
    if expected not in ("full", "damaged"):
        raise ValueError("unsupported HP expectation")
    colors = _hp_samples(image)
    if not similar(colors["stable"], GREEN):
        raise ValueError("Raider HP baseline green pixel missing")
    expected_rgb = GREEN if expected == "full" else DARK
    if not similar(colors["difference"], expected_rgb):
        raise ValueError("Raider HP bar pixel inconsistent with " + expected +
                         " expected=" + str(expected_rgb) +
                         " actual=" + str(colors["difference"]))
    return True


def exercise(initial, after_right, io):
    _require_state(initial, INITIAL_DUEL)
    _require_state(after_right, INITIAL_DUEL)
    _require_hp(initial, "full")
    start = _center(initial)
    cursor = _center(after_right)
    if cursor[0] < start[0] + 12:
        raise ValueError("initial right cursor input not observed")
    scale = decode(initial, INITIAL_DUEL)
    target = (start[0] + 40 * scale["scale_x"],
              start[1] + 20 * scale["scale_y"])
    steps = []
    # Reset to Scout, observing every frame; no gameplay Confirm yet.
    for i in range(1, 13):
        if _near(cursor, start):
            break
        if abs(cursor[1] - start[1]) > 80:
            raise ValueError("return cursor off duel row")
        direction = "Left" if cursor[0] > start[0] else "Right"
        previous = cursor
        frame = io.capture_after(direction, f"duel-return-{i}")
        _require_state(frame, INITIAL_DUEL)
        cursor = _center(frame)
        stalled = _near(cursor, previous)
        steps.append({"key": direction, "cursor_x": round(cursor[0],2),
                      "stalled": stalled})
        if stalled:
            io.focus()  # Only refocus after an observed missed X11 pulse
    if not _near(cursor, start):
        raise ValueError("duel Scout cursor not recovered within twelve observations")

    selected = io.capture_after("Return", "duel-selected")
    _require_state(selected, INITIAL_DUEL)
    chosen_proof = "action-duel-selected.png"
    if not _selected_marker(selected, start):
        io.focus()
        selected = io.capture_after("space", "duel-selected-retry")
        _require_state(selected, INITIAL_DUEL)
        chosen_proof = "action-duel-selected-retry.png"
    if not _selected_marker(selected, start):
        raise ValueError("Scout not visibly selected in duel")
    steps.append({"key": "Return", "selected": True})

    # Stage64: capture a genuine frame on the legal tile directly above Scout,
    # then return to Scout before continuing the original attack sequence.
    scale = decode(initial_frame, INITIAL_DUEL)
    preview_frame = io.capture_after("Up", "duel-move-preview")
    _require_state(preview_frame, INITIAL_DUEL)
    preview_cursor = _center(preview_frame)
    expected_preview = (start[0], start[1] - 20 * scale["scale_y"])
    if not _near(preview_cursor, expected_preview, tx=12, ty=12):
        raise ValueError("movement preview cursor did not reach the legal tile above Scout")
    if not _selected_marker(preview_frame, start):
        raise ValueError("Scout selection lost during movement preview")
    returned_preview = io.capture_after("Down", "duel-move-preview-return")
    _require_state(returned_preview, INITIAL_DUEL)
    if not _near(_center(returned_preview), start):
        raise ValueError("cursor did not return to Scout after movement preview")
    if not _selected_marker(returned_preview, start):
        raise ValueError("Scout selection lost after returning from movement preview")
    steps.append({"key": "Up", "movement_preview": True, "path_cost": 1,
                  "remaining_points": 3})
    steps.append({"key": "Down", "movement_preview_return": True})

    cursor = start
    for i in range(1, 13):
        if _near(cursor, target):
            break
        if abs(cursor[1] - target[1]) > 80:
            raise ValueError("duel aim cursor off row")
        direction = "Right" if cursor[0] < target[0] else "Left"
        previous = cursor
        frame = io.capture_after(direction, f"duel-aim-{i}")
        _require_state(frame, INITIAL_DUEL)
        cursor = _center(frame)
        stalled = _near(cursor, previous)
        steps.append({"key": direction, "aim_x": round(cursor[0],2),
                      "stalled": stalled})
        if stalled:
            io.focus()
    if not _near(cursor, target):
        raise ValueError("duel aim never reached Raider tile")

    attacked = io.capture_after("y", "duel-attacked")
    _require_state(attacked, ATTACKED_DUEL)
    _effect(attacked, "Attacked")
    _require_hp(attacked, "damaged")
    if not _selected_marker(attacked, start):
        raise ValueError("Scout selection lost after first attack")
    steps.append({"key": "y", "effect": "Attacked", "enemy_hp": 14})

    rejected = io.capture_after("y", "duel-rejected")
    _require_state(rejected, ATTACKED_DUEL)
    _effect(rejected, "Rejected")
    _require_hp(rejected, "damaged")
    if not _selected_marker(rejected, start):
        raise ValueError("Scout selection lost after rejected repeat attack")
    steps.append({"key": "y", "effect": "Rejected", "enemy_hp": 14})
    return {
        "format": "VHS44-ROM-free-duel-screenshots",
        "attack_passed": True,
        "initial_fingerprint": INITIAL_DUEL,
        "attacked_fingerprint": ATTACKED_DUEL,
        "hp_before": 20, "hp_after": 14,
        "second_attack_rejected": True,
        "selected_proof": chosen_proof,
        "movement_preview_proof": "action-duel-move-preview.png",
        "movement_preview_return_proof": "action-duel-move-preview-return.png",
        "attack_proof": "action-duel-attacked.png",
        "reject_proof": "action-duel-rejected.png",
        "steps": steps,
        "scope": "Independent ROM-free Switch NRO duel in NeXium; not Sega Saturn gameplay",
    }


def verify_folder(folder):
    report = json.loads((folder / "attack-evidence.json").read_text("utf-8"))
    if report.get("attack_passed") is not True:
        raise ValueError("live duel attack not confirmed")
    for key, value in {
        "initial_fingerprint": INITIAL_DUEL,
        "attacked_fingerprint": ATTACKED_DUEL,
        "hp_before": 20, "hp_after": 14,
        "second_attack_rejected": True,
        "attack_proof": "action-duel-attacked.png",
        "reject_proof": "action-duel-rejected.png",
    }.items():
        if report.get(key) != value:
            raise ValueError("duel receipt field mismatched: " + key)
    selected_name = report.get("selected_proof")
    if selected_name not in ("action-duel-selected.png",
                             "action-duel-selected-retry.png"):
        raise ValueError("invalid selection PNG filename")
    with Image.open(folder/"nexium-window.png") as initial, \
         Image.open(folder/selected_name) as selected, \
         Image.open(folder/"action-duel-attacked.png") as attacked, \
         Image.open(folder/"action-duel-rejected.png") as rejected:
        _require_state(initial, INITIAL_DUEL)
        _require_state(selected, INITIAL_DUEL)
        _require_hp(initial, "full")
        start = _center(initial)
        if not _selected_marker(selected, start):
            raise ValueError("real selection proof missing")
        for frame in (attacked, rejected):
            _require_state(frame, ATTACKED_DUEL)
            _require_hp(frame, "damaged")
            if not _selected_marker(frame, start):
                raise ValueError("Scout not visibly selected after attack")
        _effect(attacked, "Attacked")
        _effect(rejected, "Rejected")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window")
    parser.add_argument("--folder", type=Path, default=Path("runtime-evidence"))
    parser.add_argument("--verify-dir", type=Path)
    args = parser.parse_args()
    if args.verify_dir is not None:
        verify_folder(args.verify_dir)
        print("VH_ATTACK_NE XIUM verified=true hp=20->14 repeated=false".replace("NE XIUM","NEXIUM"))
        return
    if not args.window:
        parser.error("live duel requires --window")
    args.folder.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(args.folder/"nexium-window.png") as before, \
             Image.open(args.folder/"nexium-after-right.png") as after:
            report = exercise(before.convert("RGB"), after.convert("RGB"),
                              RealX11(args.window, args.folder))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        report = {"format": "VHS44-ROM-free-duel-screenshots",
                  "attack_passed": False, "error_type": type(error).__name__,
                  "error": str(error)}
    (args.folder/"attack-evidence.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["attack_passed"]:
        raise SystemExit("live Stage44 attack evidence not verified")


if __name__ == "__main__":
    main()
