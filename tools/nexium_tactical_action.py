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
        if key not in ("Left", "Right", "Return"):
            raise ValueError("unexpected action key")
        subprocess.run(["timeout", "--kill-after=1s", "4s", "xdotool",
                        "key", "--clearmodifiers", "--window", self.window, key],
                       check=True, timeout=7, stdout=subprocess.DEVNULL)
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
    steps.append({"key":"Return", "purpose":"select_scout"})
    aimed = io.capture_after("Right", "aimed")
    _require_state(aimed, INITIAL)
    at = _center(aimed)
    if not _near(at, target):
        if _near(at, start):  # missed input: retry once without claiming success
            io.focus()
            aimed = io.capture_after("Right", "aimed-retry")
            _require_state(aimed, INITIAL)
            at = _center(aimed)
            steps.append({"key":"Right", "purpose":"aim_retry"})
        if not _near(at, target):
            raise ValueError("aim cursor did not reach exactly one tile right")
    steps.append({"key":"Right", "purpose":"aim_scout_move"})
    moved = io.capture_after("Return", "moved")
    final = _require_state(moved, AFTER_SCOUT_MOVE)
    steps.append({"key":"Return", "purpose":"commit_move"})
    return {
        "format":"VHS40-ROM-free-action-observation",
        "action_passed":True, "initial_fingerprint":first,
        "after_move_fingerprint":final, "cursor_returned_to_scout":True,
        "aimed_exactly_one_tile":True, "steps":steps,
        "scope":"X11 keyboard into ROM-free guest; NOT physical Switch controller or original Saturn scene"
    }


def verify_folder(folder):
    report = json.loads((folder/"action-evidence.json").read_text(encoding="utf-8"))
    if report.get("action_passed") is not True:
        raise ValueError("tactical action did not pass")
    if report.get("initial_fingerprint") != INITIAL or report.get("after_move_fingerprint") != AFTER_SCOUT_MOVE:
        raise ValueError("wrong action receipt fingerprint")
    with Image.open(folder/"nexium-window.png") as first, Image.open(folder/"action-moved.png") as moved:
        _require_state(first, INITIAL)
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
        report = {"format":"VHS40-ROM-free-action-observation",
                  "action_passed":False, "error_type":type(error).__name__, "error":str(error)}
    (folder/"action-evidence.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    if not report["action_passed"]:
        raise SystemExit("real tactical move not confirmed")


if __name__ == "__main__":
    main()
