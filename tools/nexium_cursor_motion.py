#!/usr/bin/env python3
"""Compare two *actual* NeXium screenshots for a plausible cursor move.

The yellow terrain cursor is a component, independent of SDL debug logging.
A pass is a visual movement heuristic, not evidence of gamepad support or
reconstructed Sega Saturn gameplay. No game data is read/exported.
"""
from __future__ import annotations
import argparse
from collections import deque
import json
from pathlib import Path
from PIL import Image


def yellow_center(image: Image.Image) -> tuple[float, float, int] | None:
    """Return center/area of the largest contiguous yellow terrain region."""
    rgb = image.convert('RGB')
    w, h = rgb.size
    if not (640 <= w <= 8192 and 360 <= h <= 8192):
        raise ValueError('Invalid screenshot dimensions')
    pixels = rgb.load()
    candidates = set()
    for y in range(round(h * 0.08), round(h * 0.76)):
        for x in range(w):
            r, g, b = pixels[x, y]
            if 192 <= r <= 255 and 142 <= g <= 220 and 35 <= b <= 110 and r > g + 12 and g > b + 45:
                candidates.add(y * w + x)
    largest = None
    while candidates:
        root = candidates.pop()
        pending = deque([root]); mass = 0; minx = w; miny = h; maxx = maxy = 0
        while pending:
            pos = pending.popleft()
            x, y = pos % w, pos // w
            mass += 1
            minx = min(minx, x); maxx = max(maxx, x)
            miny = min(miny, y); maxy = max(maxy, y)
            for nei in (pos-w, pos+w, pos-1 if x else -1, pos+1 if x+1<w else -1):
                if nei in candidates:
                    candidates.remove(nei); pending.append(nei)
        if mass >= 90 and maxx-minx >= 14 and maxy-miny >= 8 and (largest is None or mass > largest[2]):
            largest = ((minx+maxx)/2, (miny+maxy)/2, mass)
    return largest


def evaluate_motion(before: Image.Image, after: Image.Image) -> dict:
    if before.size != after.size:
        raise ValueError('Screenshots must have identical dimensions')
    w, h = before.size
    previous = yellow_center(before)
    current = yellow_center(after)
    dx = (current[0] - previous[0]) if previous and current else None
    dy = (current[1] - previous[1]) if previous and current else None
    # In our *synthetic* isometric training scene, Right moves cursor +40,+20
    # logical pixels on a 1280x720 surface. Require a meaningful positive
    # x delta, but allow scaling and different window chrome.
    moved = bool(dx is not None and dy is not None and dx >= max(6, w * 0.009)
                 and dy >= -h * 0.025 and dy <= h * 0.15)
    return {
        'before_cursor_detected': previous is not None,
        'after_cursor_detected': current is not None,
        'delta_x_pixels': round(dx, 2) if dx is not None else None,
        'delta_y_pixels': round(dy, 2) if dy is not None else None,
        'plausible_right_cursor_movement': moved,
        'limitations': 'Non-authoritative screenshot heuristic; never proves guest input without separate log review.'
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    with Image.open(args.before) as b, Image.open(args.after) as a:
        result = evaluate_motion(b, a)
    payload = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(payload, encoding='utf-8')
    print(payload, end='')
    if not result['plausible_right_cursor_movement']:
        raise SystemExit('Cursor motion unconfirmed; inspect NeXium evidence')


if __name__ == '__main__':
    main()
