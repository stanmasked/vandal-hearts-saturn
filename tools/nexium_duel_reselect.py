#!/usr/bin/env python3
"""Stage45: screenshot-proved cancel/reselect/re-attack in the ROM-free duel.

Run only after the genuine Stage44 NeXium attack passed. An X11 key being
sent is never interpreted as a successful tactical action.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from PIL import Image
from tools.nexium_attack_action import ATTACKED_DUEL, _require_hp, verify_folder as verify_attack
from tools.nexium_tactical_action import RealX11, _center, _near, _require_state, _selected_marker
from tools.nexium_post_move import _effect


def navigate(io, start, goal, name, observations):
    """Bounded horizontal correction, with focus only on a witnessed stall."""
    current = start
    for i in range(1, 13):
        if _near(current, goal):
            return current
        if abs(current[1] - goal[1]) > 80:
            raise ValueError(name + " cursor left expected map row")
        direction = "Left" if current[0] > goal[0] else "Right"
        previous = current
        image = io.capture_after(direction, f"reselect-{name}-{i}")
        _require_state(image, ATTACKED_DUEL)
        _require_hp(image, "damaged")
        current = _center(image)
        stalled = _near(current, previous)
        observations.append({"key": direction, "phase": name,
                             "cursor_x": round(current[0], 2),
                             "cursor_y": round(current[1], 2),
                             "stalled": stalled})
        if stalled:
            io.focus()
    if not _near(current, goal):
        raise ValueError(name + " cursor not reached within twelve observations")
    return current


def exercise(initial, rejected_before, io):
    _require_state(initial, "9376e23745926630")
    _require_state(rejected_before, ATTACKED_DUEL)
    _effect(rejected_before, "Rejected")
    _require_hp(rejected_before, "damaged")
    scout = _center(initial)
    enemy = _center(rejected_before)
    if not _selected_marker(rejected_before, scout):
        raise ValueError("Stage44 ending has no selected Scout")
    if enemy[0] <= scout[0] + 12:
        raise ValueError("Stage44 cursor did not aim at Raider")

    steps = []
    cancelled = io.capture_after("BackSpace", "reselect-cancelled")
    _require_state(cancelled, ATTACKED_DUEL)
    _require_hp(cancelled, "damaged")
    _effect(cancelled, "Cancelled")
    if _selected_marker(cancelled, scout):
        raise ValueError("Scout outline not cleared by cancellation")
    if not _near(_center(cancelled), enemy):
        raise ValueError("cancel unexpectedly moved cursor")
    steps.append({"key": "BackSpace", "effect": "Cancelled", "hp": 14})

    navigate(io, _center(cancelled), scout, "return", steps)
    selected = io.capture_after("Return", "reselect-selected")
    _require_state(selected, ATTACKED_DUEL)
    _require_hp(selected, "damaged")
    selected_file = "action-reselect-selected.png"
    if not _selected_marker(selected, scout):
        io.focus()
        selected = io.capture_after("space", "reselect-selected-retry")
        _require_state(selected, ATTACKED_DUEL)
        _require_hp(selected, "damaged")
        selected_file = "action-reselect-selected-retry.png"
    if not _selected_marker(selected, scout):
        raise ValueError("Scout re-selection never appeared")
    _effect(selected, "Selected")
    if not _near(_center(selected), scout):
        raise ValueError("reselection cursor on wrong tile")
    steps.append({"key": "Return/space", "effect": "Selected", "hp": 14})

    navigate(io, scout, enemy, "aim", steps)
    rejected = io.capture_after("y", "reselect-rejected")
    _require_state(rejected, ATTACKED_DUEL)
    _require_hp(rejected, "damaged")
    _effect(rejected, "Rejected")
    if not _selected_marker(rejected, scout):
        raise ValueError("rejected re-attack lost Scout selection")
    if not _near(_center(rejected), enemy):
        raise ValueError("re-attack cursor moved away from Raider")
    steps.append({"key": "y", "effect": "Rejected", "hp": 14})
    return {
        "format": "VHS45-ROM-free-duel-reselect-v1",
        "reselect_passed": True,
        "attacked_fingerprint": ATTACKED_DUEL,
        "hp_after": 14,
        "cancelled_proof": "action-reselect-cancelled.png",
        "selected_proof": selected_file,
        "rejected_proof": "action-reselect-rejected.png",
        "repeat_attack_after_reselect_rejected": True,
        "steps": steps,
        "scope": "Synthetic duel homebrew in NeXium, not original Saturn gameplay",
    }


def verify_folder(folder):
    verify_attack(folder)
    report = json.loads((folder / "reselect-evidence.json").read_text("utf-8"))
    for name, value in {
        "reselect_passed": True,
        "attacked_fingerprint": ATTACKED_DUEL,
        "hp_after": 14,
        "repeat_attack_after_reselect_rejected": True,
        "cancelled_proof": "action-reselect-cancelled.png",
        "rejected_proof": "action-reselect-rejected.png",
    }.items():
        if report.get(name) != value:
            raise ValueError("Stage45 receipt missing: " + name)
    selected_name = report.get("selected_proof")
    if selected_name not in ("action-reselect-selected.png",
                             "action-reselect-selected-retry.png"):
        raise ValueError("untrusted reselected screenshot filename")
    with Image.open(folder / "nexium-window.png") as initial, \
         Image.open(folder / "action-duel-rejected.png") as earlier, \
         Image.open(folder / "action-reselect-cancelled.png") as cancelled, \
         Image.open(folder / selected_name) as selected, \
         Image.open(folder / "action-reselect-rejected.png") as rejected:
        scout = _center(initial)
        enemy = _center(earlier)
        if not _selected_marker(earlier, scout):
            raise ValueError("initial attack did not leave Scout selected")
        for frame in (earlier, cancelled, selected, rejected):
            _require_state(frame, ATTACKED_DUEL)
            _require_hp(frame, "damaged")
        _effect(cancelled, "Cancelled")
        _effect(selected, "Selected")
        _effect(rejected, "Rejected")
        if _selected_marker(cancelled, scout):
            raise ValueError("cancel PNG still shows selected Scout")
        if not _selected_marker(selected, scout) or not _selected_marker(rejected, scout):
            raise ValueError("reselect/attack outline is missing")
        if not _near(_center(cancelled), enemy):
            raise ValueError("cancellation cursor mismatch")
        if not _near(_center(selected), scout):
            raise ValueError("reselection cursor mismatch")
        if not _near(_center(rejected), enemy):
            raise ValueError("repeat attack cursor mismatch")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window")
    parser.add_argument("--folder", type=Path, default=Path("runtime-evidence"))
    parser.add_argument("--verify-dir", type=Path)
    args = parser.parse_args()
    if args.verify_dir is not None:
        verify_folder(args.verify_dir)
        print("VH_DUEL_RESELECT verified=true reattack_rejected=true")
        return
    if not args.window:
        parser.error("live Stage45 requires --window")
    args.folder.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(args.folder / "nexium-window.png") as initial, \
             Image.open(args.folder / "action-duel-rejected.png") as rejected:
            report = exercise(initial.convert("RGB"), rejected.convert("RGB"),
                              RealX11(args.window, args.folder))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        report = {"format": "VHS45-ROM-free-duel-reselect-v1",
                  "reselect_passed": False, "error_type": type(error).__name__,
                  "error": str(error)}
    (args.folder / "reselect-evidence.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["reselect_passed"]:
        raise SystemExit("Stage45 real NeXium re-selection not confirmed")


if __name__ == "__main__":
    main()
