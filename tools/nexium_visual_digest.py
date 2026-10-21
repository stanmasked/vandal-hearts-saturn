#!/usr/bin/env python3
"""Decode a ROM-free debug state hash from scaled NeXium window screenshots.

Three magenta registration marks calibrate screen pixel scale/translation.
Pixel data is independent of the emulator's upper-left performance display.
Not evidence of authentic Sega Saturn game state or stable input by itself.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
from PIL import Image

INITIAL_TRAINING_FINGERPRINT = 'ae38b0b5ab887f00'
ANCHORS = ((1028, 16), (1180, 16), (1028, 168))
ANCHOR_SIZE = 10
ANCHOR_RGB = (234, 40, 190)
OFF_RGB = (40, 53, 69)
ON_RGB = (66, 220, 132)
X, Y, PITCH, SIZE = 1050, 38, 14, 10


def similar(color, expected, tolerance=27):
    return all(abs(a - b) <= tolerance for a, b in zip(color[:3], expected))


def _magenta_components(image):
    """Find distinct, square anchor regions in the unobstructed top-right ROI."""
    pixels = image.load()
    width, height = image.size
    active = set()
    for y in range(max(0, int(height * .005)), min(height, int(height * .40))):
        for x in range(int(width * .75), width):
            if similar(pixels[x, y], ANCHOR_RGB):
                active.add(y * width + x)
    parts = []
    while active:
        seed = active.pop()
        queue = deque((seed,))
        minx = width; maxx = -1; miny = height; maxy = -1; count = 0
        while queue:
            v = queue.popleft()
            x, y = v % width, v // width
            count += 1
            minx = min(minx, x); maxx = max(maxx, x)
            miny = min(miny, y); maxy = max(maxy, y)
            for nearby in (v - width, v + width, v - 1 if x else -1,
                           v + 1 if x + 1 < width else -1):
                if nearby in active:
                    active.remove(nearby)
                    queue.append(nearby)
        if count >= 20 and maxx-minx >= 4 and maxy-miny >= 4:
            parts.append(((minx+maxx)/2, (miny+maxy)/2, count))
    return parts


def _calibration(parts):
    if len(parts) != 3:
        return None
    by_y = sorted(parts, key=lambda a: a[1])
    left, right = sorted(by_y[:2], key=lambda a: a[0])
    bottom = by_y[2]
    # The three anchors make a right angle with 152 logical pixels per leg.
    dx = right[0] - left[0]
    dy = bottom[1] - left[1]
    if not (105 < dx < 195 and 105 < dy < 195):
        return None
    if abs(right[1]-left[1]) > 10 or abs(bottom[0]-left[0]) > 10:
        return None
    return left, dx/152, dy/152


def decode(image: Image.Image, expected: str = INITIAL_TRAINING_FINGERPRINT) -> dict:
    if len(expected) != 16 or any(c not in '0123456789abcdefABCDEF' for c in expected):
        raise ValueError('Expected exactly 16 hexadecimal digits')
    w, h = image.size
    if not (900 <= w <= 1920 and 550 <= h <= 1200):
        raise ValueError('Unexpected NeXium window dimensions')
    rgb = image.convert('RGB')
    anchors = _magenta_components(rgb)
    calibrated = _calibration(anchors)
    detected = len(anchors)
    fingerprint = 0
    unrecognized = 64
    sx = sy = None
    if calibrated is not None:
        corner, sx, sy = calibrated
        pixels = rgb.load()
        unrecognized = 0
        left_center = ANCHORS[0][0] + (ANCHOR_SIZE-1)/2
        top_center = ANCHORS[0][1] + (ANCHOR_SIZE-1)/2
        for bit in range(64):
            logical_x = X + (bit % 8)*PITCH + SIZE//2
            logical_y = Y + (bit // 8)*PITCH + SIZE//2
            x = round(corner[0] + (logical_x-left_center)*sx)
            y = round(corner[1] + (logical_y-top_center)*sy)
            if not (0 <= x < w and 0 <= y < h):
                unrecognized += 1
                continue
            value = pixels[x, y]
            if similar(value, ON_RGB):
                fingerprint |= 1 << bit
            elif not similar(value, OFF_RGB):
                unrecognized += 1
    actual = f'{fingerprint:016x}' if unrecognized == 0 and calibrated is not None else None
    return {
        'format': 'VHS1-ROM-free-visual-fnv64',
        'width': w, 'height': h,
        'anchors_found': detected,
        'registration_geometry_valid': calibrated is not None,
        'scale_x': round(sx, 4) if sx is not None else None,
        'scale_y': round(sy, 4) if sy is not None else None,
        'unrecognized_cells': unrecognized,
        'decoded_fingerprint': actual,
        'expected_fingerprint': expected.lower(),
        'matches_expected_training_state': bool(calibrated is not None and actual == expected.lower()),
        'limitation': ('ROM-free visual state signature only. Does not prove original Saturn '
                       'fidelity, guest controls, or clean emulator shutdown.'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('screenshot', type=Path)
    parser.add_argument('--expected', default=INITIAL_TRAINING_FINGERPRINT)
    parser.add_argument('--output', type=Path)
    options = parser.parse_args()
    with Image.open(options.screenshot) as im:
        result = decode(im, options.expected)
    report = json.dumps(result, indent=2) + '\n'
    if options.output:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(report, encoding='utf-8')
    print(report, end='')
    if not result['matches_expected_training_state']:
        raise SystemExit('NeXium visual signature missing or wrong')

if __name__ == '__main__':
    main()
