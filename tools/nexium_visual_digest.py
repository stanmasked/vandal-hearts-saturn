#!/usr/bin/env python3
"""Decode ROM-free C++ battle fingerprint from the *actual* NeXium screenshot.

This is a cross-platform debugging marker, not original Sega Saturn graphics.
The 1280x720 screenshot and fixed overlay layout are explicit requirements;
no OCR, external assets, or confidential game data are required.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

INITIAL_TRAINING_FINGERPRINT = "ae38b0b5ab887f00"
ANCHORS = ((8, 8), (116, 8), (8, 116))
ANCHOR_RGB = (234, 40, 190)
OFF_RGB = (40, 53, 69)
ON_RGB = (66, 220, 132)
X, Y, PITCH, SIZE = 20, 20, 12, 8


def similar(pixel: tuple[int, ...], expected: tuple[int, int, int], tolerance: int = 20) -> bool:
    return all(abs(a - b) <= tolerance for a, b in zip(pixel[:3], expected))


def center_pixel(pixels, x: int, y: int):
    return pixels[x + SIZE // 2, y + SIZE // 2]


def decode(image: Image.Image, expected: str = INITIAL_TRAINING_FINGERPRINT) -> dict:
    if image.size != (1280, 720):
        raise ValueError("Expected an unscaled 1280x720 guest framebuffer")
    if len(expected) != 16 or any(c not in "0123456789abcdefABCDEF" for c in expected):
        raise ValueError("Expected exactly 16 hex digits")
    pixels = image.convert("RGB").load()
    anchors_found = sum(similar(center_pixel(pixels, x, y), ANCHOR_RGB) for x, y in ANCHORS)
    hash_value = 0
    unknown = 0
    for bit in range(64):
        sample = center_pixel(pixels, X + (bit % 8) * PITCH, Y + (bit // 8) * PITCH)
        if similar(sample, ON_RGB):
            hash_value |= 1 << bit
        elif not similar(sample, OFF_RGB):
            unknown += 1
    actual = f"{hash_value:016x}" if unknown == 0 else None
    matched = bool(anchors_found == 3 and unknown == 0 and actual == expected.lower())
    return {
        "format": "VHS1-ROM-free-visual-fnv64",
        "width": image.width,
        "height": image.height,
        "anchors_found": anchors_found,
        "unrecognized_cells": unknown,
        "decoded_fingerprint": actual,
        "expected_fingerprint": expected.lower(),
        "matches_expected_training_state": matched,
        "limitation": (
            "Confirms only a screen-encoded synthetic tactics checksum. "
            "It does not prove input delivery, stable NeXium shutdown, or Saturn-game fidelity."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshot", type=Path)
    parser.add_argument("--expected", default=INITIAL_TRAINING_FINGERPRINT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with Image.open(args.screenshot) as image:
        result = decode(image, expected=args.expected)
    payload = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    if not result["matches_expected_training_state"]:
        raise SystemExit("Visual state digest absent, damaged or mismatched")


if __name__ == "__main__":
    main()
