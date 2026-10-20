#!/usr/bin/env python3
"""ROM-free NeXium tactical action trace: verify a real Scout move on pixels.

Starts AFTER the existing screenshot-confirmed Right cursor probe, and
navigates back to the initial Scout. Never uses original Sega Saturn assets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import time

from PIL import Image
from tools.nexium_cursor_motion import yellow_center
from tools.nexium_visual_digest import decode

INITIAL = "ae38b0b5ab887f00"
AFTER_SCOUT_MOVE = "ef9c7d67953c9b2a"


def _center(image):
    value = yellow_center(image)
    if value is None:
        raise ValueError("yellow training cursor not visible")
    return value[:2]


def _near(a, b, tx=12, ty=12):
    return abs(a[0]-b[0]) <= tx and abs(a[1]-b[1]) <= ty


def _selected_marker(image, cursor):
    """Detect the SDL-selected Scout outline, distinct from yellow terrain.

    The training app draws this 251/220/90 border above the unit; mere
    cursor navigation does not. Only a local region around Scout is used.
    """
    rgb = image.convert("RGB")
    w, h = rgb.size
    cx, cy = cursor
    count = 0
    for y in range(max(0, round(cy-90)), min(h, round(cy+15))):
        for x in range(max(0, round(cx-45)), min(w, round(cx+46))):
            r, g, b = rgb.getpixel((x, y))
            if r >= 235 and 195 <= g <= 245 and 55 <= b <= 135 and r > g + 14:
                count += 1
                if count >= 12:
                    return True
    return False


def _require_state(image, expected):
    record = decode(image, expected)
    if not record["matches_expected_training_state"]:
        raise ValueError("guest visual tactical checksum mismatch: " + str(record["decoded_fingerprint"]))
    return record["decoded_fingerprint"]


class RealX11:
    def __init__(self, window, folder):
        if not window.isdecimal() or not 0 < int(window) <= 0xffffffff:
            raise ValueError("invalid numeric X11 window")
        self.window, self.folder = window, folder

    def capture_after(self, key, label):
        if key not in ("Left", "Right", "Return", "space", "BackSpace", "y"):
            raise ValueError("unexpected action key")
        # Genuine Stage41 screenshots show short arrows work (one tile), but
        # a default 12 ms Return can be missed by the guest frame sampler.
        # Use a 180 ms pulse for Confirm/Space, below SDL's key-repeat delay.
        command = ["timeout", "--kill-after=1s", "4s", "xdotool",
                   "key", "--clearmodifiers", "--delay",
                   "0" if key in ("Left", "Right") else "180",
                   "--window", self.window, key]
        subprocess.run(command, check=True, timeout=7, stdout=subprocess.DEVNULL)
        time.sleep(0.9)
        filename = self.folder / f"action-{label}.png"
        subprocess.run(["timeout", "--kill-after=1s", "8s", "import",
                        "-window", self.window, str(filename)],
                       check=True, timeout=11, stdout=subprocess.DEVNULL)
        with Image.open(filename) as image:
            return image.convert("RGB")

    def focus(self):
        # Never block waiting for WM activation. Failure does not fake input.
        subprocess.run(["timeout", "--kill-after=1s", "2s", "xdotool",
                        "windowfocus", self.window], check=False, timeout=5,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def exercise(initial_frame, after_right, io):
    """Accept only an observed one-tile move changing the entire battle hash."""
    first = _require_state(initial_frame, INITIAL)
    _require_state(after_right, INITIAL)
    start = _center(initial_frame)
    current = _center(after_right)
    scale = decode(initial_frame, INITIAL)
    target = (start[0] + 40*scale["scale_x"], start[1] + 20*scale["scale_y"])
    steps = []
    if current[0] <= start[0] + 12:
        raise ValueError("precondition failed: earlier Right cursor did not move")
    # Real NeXium run #39469307751 proved a *single* Left can jump two
    # tiles: cursor x=524.5 -> 442.0, overshooting Scout x=490.5.
    # Correct the direction after EVERY captured frame, never blindly
    # dispatch more Left presses when already left of the target.
    for index in range(1, 9):
        if _near(current, start):
            break
        if abs(current[1] - start[1]) > 80:
            raise ValueError("return cursor left the Scout map row")
        direction = "Left" if current[0] > start[0] else "Right"
        frame = io.capture_after(direction, f"return-{index}")
        _require_state(frame, INITIAL)
        current = _center(frame)
        steps.append({"key":direction, "cursor_x":round(current[0],2),
                      "cursor_y":round(current[1],2)})
    if not _near(current, start):
        raise ValueError("could not return cursor to initial Scout tile after 8 observations")
    selected = io.capture_after("Return", "selected")
    _require_state(selected, INITIAL)  # selection must not move tactical units
    selected_proof = "action-selected.png"
    steps.append({"key":"Return", "purpose":"select_scout",
                  "selected_outline_seen":_selected_marker(selected,start)})
    if not _selected_marker(selected, start):
        # An X11 Return dispatch alone is not proof SDL selected Scout.
        # One bounded Space fallback (same SDL Confirm action) is permitted.
        io.focus()
        selected = io.capture_after("space", "selected-retry")
        _require_state(selected, INITIAL)
        selected_proof = "action-selected-retry.png"
        steps.append({"key":"space", "purpose":"select_scout_retry",
                      "selected_outline_seen":_selected_marker(selected,start)})
    if not _selected_marker(selected,start):
        raise ValueError("Scout selection outline not visible after two confirmations")
    # Stage40 live evidence showed Right can jump *two* cells: the captured
    # starting center (490.5,251) became (562.5,285.5). Do not commit from
    # that cell. Aim from observed pixels, correcting in either direction.
    at = start
    for attempt in range(1, 9):
        if _near(at, target):
            break
        if abs(at[1] - target[1]) > 80:
            raise ValueError("aim cursor left the Scout map row")
        direction = "Right" if at[0] < target[0] else "Left"
        previous = at
        aimed = io.capture_after(direction, f"aim-{attempt}")
        _require_state(aimed, INITIAL)
        at = _center(aimed)
        steps.append({"key":direction, "purpose":"aim_scout_move",
                      "cursor_x":round(at[0],2), "cursor_y":round(at[1],2)})
        if _near(at, previous) and not _near(at, target):
            io.focus()  # only an observed missed pulse authorizes refocus
    if not _near(at, target):
        raise ValueError("aim cursor did not reach exactly one tile right after 8 observations")
    moved = io.capture_after("Return", "moved")
    final_proof = "action-moved.png"
    last = decode(moved, AFTER_SCOUT_MOVE)
    steps.append({"key":"Return", "purpose":"commit_move",
                  "observed_fingerprint":last["decoded_fingerprint"]})
    if not last["matches_expected_training_state"]:
        # Retry only if no battle-state change occurred at all; never try to
        # force a success after a different or unrecognized guest state.
        _require_state(moved, INITIAL)
        io.focus()
        moved = io.capture_after("space", "moved-retry")
        final_proof = "action-moved-retry.png"
        steps.append({"key":"space", "purpose":"commit_move_retry"})
    final = _require_state(moved, AFTER_SCOUT_MOVE)
    return {
        "format":"VHS42-ROM-free-action-observation",
        "action_passed":True, "initial_fingerprint":first,
        "after_move_fingerprint":final, "cursor_returned_to_scout":True,
        "aimed_exactly_one_tile":True, "steps":steps,
        "selected_proof":selected_proof, "moved_proof":final_proof,
        "scope":"X11 keyboard into ROM-free guest; NOT physical Switch controller or original Saturn scene"
    }


def verify_folder(folder):
    report = json.loads((folder/"action-evidence.json").read_text(encoding="utf-8"))
    if report.get("action_passed") is not True:
        raise ValueError("tactical action did not pass")
    if report.get("initial_fingerprint") != INITIAL or report.get("after_move_fingerprint") != AFTER_SCOUT_MOVE:
        raise ValueError("wrong action receipt fingerprint")
    selected_name = report.get("selected_proof")
    moved_name = report.get("moved_proof")
    if selected_name not in ("action-selected.png", "action-selected-retry.png"):
        raise ValueError("missing valid selection evidence filename")
    if moved_name not in ("action-moved.png", "action-moved-retry.png"):
        raise ValueError("missing valid moved evidence filename")
    with Image.open(folder/"nexium-window.png") as first, \
         Image.open(folder/selected_name) as selected, \
         Image.open(folder/moved_name) as moved:
        _require_state(first, INITIAL)
        _require_state(selected, INITIAL)
        if not _selected_marker(selected,_center(first)):
            raise ValueError("Scout selection not observed in actual screenshot")
        _require_state(moved, AFTER_SCOUT_MOVE)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window")
    parser.add_argument("--folder", type=Path, default=Path("runtime-evidence"))
    parser.add_argument("--verify-dir", type=Path)
    args = parser.parse_args()
    if args.verify_dir:
        verify_folder(args.verify_dir)
        print("VH_TACTICAL_ACTION verified=true initial="+INITIAL+" moved="+AFTER_SCOUT_MOVE)
        return
    if not args.window:
        parser.error("live tactical trace requires --window")
    folder = args.folder
    folder.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(folder/"nexium-window.png") as before, Image.open(folder/"nexium-after-right.png") as after:
            report = exercise(before.convert("RGB"), after.convert("RGB"), RealX11(args.window,folder))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        report = {"format":"VHS42-ROM-free-action-observation",
                  "action_passed":False, "error_type":type(error).__name__, "error":str(error)}
    (folder/"action-evidence.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    if not report["action_passed"]:
        raise SystemExit("real tactical move not confirmed")


if __name__ == "__main__":
    main()
