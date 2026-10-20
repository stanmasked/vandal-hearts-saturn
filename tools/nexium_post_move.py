#!/usr/bin/env python3
"""Stage43: inspect real guest pixels after a completed ROM-free Scout move.

Require an acknowledged REJECTED second move and CANCELLED selection.
Never infer success from delivered X11 keys or unchanged checksum alone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from PIL import Image
from tools.nexium_tactical_action import (
    AFTER_SCOUT_MOVE, INITIAL, RealX11, _center, _near, _require_state,
    _selected_marker,
)
from tools.nexium_visual_digest import (
    ANCHORS, ANCHOR_SIZE, _calibration, _magenta_components, similar,
)

RECEIPT_AT = (1218, 68)
COLORS = {
    "Moved": (66, 220, 132),
    "Rejected": (239, 79, 76),
    "Cancelled": (251, 220, 90),
    "Attacked": (179, 103, 244),
    "Selected": (63, 167, 239),
}


def _effect(image, expected):
    """Sample the registered, guest-rendered last-effect square."""
    if expected not in COLORS:
        raise ValueError("unknown action receipt")
    rgb = image.convert("RGB")
    registration = _calibration(_magenta_components(rgb))
    if registration is None:
        raise ValueError("action receipt registration missing")
    anchor, sx, sy = registration
    start_x = ANCHORS[0][0] + (ANCHOR_SIZE - 1) / 2
    start_y = ANCHORS[0][1] + (ANCHOR_SIZE - 1) / 2
    x = round(anchor[0] + (RECEIPT_AT[0] - start_x) * sx)
    y = round(anchor[1] + (RECEIPT_AT[1] - start_y) * sy)
    if not (0 <= x < rgb.width and 0 <= y < rgb.height):
        raise ValueError("action receipt outside screenshot")
    value = rgb.getpixel((x, y))
    if not similar(value, COLORS[expected]):
        raise ValueError("guest action receipt not " + expected +
                         ": observed RGB=" + str(value))
    return True


def exercise(initial, moved, io):
    _require_state(initial, INITIAL)
    _require_state(moved, AFTER_SCOUT_MOVE)
    _effect(moved, "Moved")
    start = _center(initial)
    current = _center(moved)
    moved_tile = current
    if not _selected_marker(moved, moved_tile):
        raise ValueError("moved Scout must remain selected before follow-up")

    steps = []
    # Navigate back to vacated (1,5); do not touch the moved unit at (2,5).
    for index in range(1, 9):
        if _near(current, start):
            break
        if abs(current[1] - start[1]) > 80:
            raise ValueError("post-move cursor left the Scout map row")
        key = "Left" if current[0] > start[0] else "Right"
        frame = io.capture_after(key, f"post-return-{index}")
        _require_state(frame, AFTER_SCOUT_MOVE)
        current = _center(frame)
        steps.append({"key": key, "cursor": [round(current[0], 2),
                                            round(current[1], 2)]})
    if not _near(current, start):
        raise ValueError("post-move return to vacated tile not observed")

    # A bare unchanged fingerprint could also mean dropped Return; require
    # explicit guest-rendered Rejected acknowledgement and still-selected unit.
    rejected = io.capture_after("Return", "post-rejected")
    _require_state(rejected, AFTER_SCOUT_MOVE)
    _effect(rejected, "Rejected")
    if not _near(_center(rejected), start):
        raise ValueError("cursor left vacated tile during rejected move")
    if not _selected_marker(rejected, moved_tile):
        raise ValueError("rejected move unexpectedly deselected Scout")
    steps.append({"key": "Return", "receipt": "Rejected"})

    cancelled = io.capture_after("BackSpace", "post-cancelled")
    _require_state(cancelled, AFTER_SCOUT_MOVE)
    _effect(cancelled, "Cancelled")
    if _selected_marker(cancelled, moved_tile):
        raise ValueError("Scout selection outline remained after Cancel")
    steps.append({"key": "BackSpace", "receipt": "Cancelled"})
    return {
        "format": "VHS43-ROM-free-post-move",
        "post_passed": True,
        "moved_fingerprint": AFTER_SCOUT_MOVE,
        "second_move_rejected": True,
        "selection_cancelled": True,
        "rejected_proof": "action-post-rejected.png",
        "cancelled_proof": "action-post-cancelled.png",
        "steps": steps,
        "scope": "NeXium ROM-free guest; not original Sega Saturn battle",
    }


def verify_folder(folder):
    report = json.loads((folder / "post-move-evidence.json").read_text("utf-8"))
    if report.get("post_passed") is not True:
        raise ValueError("Stage43 guest continuation not passed")
    if (report.get("moved_fingerprint") != AFTER_SCOUT_MOVE or
            report.get("second_move_rejected") is not True or
            report.get("selection_cancelled") is not True):
        raise ValueError("incomplete post-move receipt")
    if (report.get("rejected_proof") != "action-post-rejected.png" or
            report.get("cancelled_proof") != "action-post-cancelled.png"):
        raise ValueError("untrusted post-move proof filenames")
    with Image.open(folder / "nexium-window.png") as initial, \
         Image.open(folder / "action-moved.png") as moved, \
         Image.open(folder / "action-post-rejected.png") as rejected, \
         Image.open(folder / "action-post-cancelled.png") as cancelled:
        _require_state(initial, INITIAL)
        for frame in (moved, rejected, cancelled):
            _require_state(frame, AFTER_SCOUT_MOVE)
        _effect(moved, "Moved")
        _effect(rejected, "Rejected")
        _effect(cancelled, "Cancelled")
        tile = _center(moved)
        if not _selected_marker(moved, tile):
            raise ValueError("selection absent from move screenshot")
        if not _selected_marker(rejected, tile):
            raise ValueError("selection absent from rejected screenshot")
        if _selected_marker(cancelled, tile):
            raise ValueError("selection still visible after cancellation")
        if not _near(_center(rejected), _center(initial)):
            raise ValueError("rejected action occurred away from vacated tile")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window")
    parser.add_argument("--folder", type=Path, default=Path("runtime-evidence"))
    parser.add_argument("--verify-dir", type=Path)
    args = parser.parse_args()
    if args.verify_dir is not None:
        verify_folder(args.verify_dir)
        print("VH_POST_MOVE verified=true reject=true cancel=true")
        return
    if not args.window:
        parser.error("live Stage43 requires --window")
    args.folder.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(args.folder / "nexium-window.png") as before, \
             Image.open(args.folder / "action-moved.png") as moved:
            report = exercise(before.convert("RGB"), moved.convert("RGB"),
                              RealX11(args.window, args.folder))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        report = {
            "format": "VHS43-ROM-free-post-move", "post_passed": False,
            "error_type": type(error).__name__, "error": str(error),
        }
    (args.folder / "post-move-evidence.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["post_passed"]:
        raise SystemExit("Stage43 post-move guest checks unverified")


if __name__ == "__main__":
    main()
