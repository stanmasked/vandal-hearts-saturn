#!/usr/bin/env python3
"""Check that a NeXium screenshot resembles our ROM-free four-unit scene.

This is a conservative visual smoke heuristic, not proof of responsive controls,
original Saturn artwork, or correct gameplay. Requires Pillow.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
from PIL import Image


def _is_ally(r: int, g: int, b: int) -> bool:
    return 35 <= r <= 140 and 120 <= g <= 225 and 160 <= b <= 255 and b > r + 55


def _is_enemy(r: int, g: int, b: int) -> bool:
    return 180 <= r <= 255 and 25 <= g <= 145 and 25 <= b <= 145 and r > g + 70


def color_components(image: Image.Image, predicate, min_area: int = 30) -> list[dict]:
    """Return coarse bounding boxes for connected colored regions above legend area."""
    rgb = image.convert('RGB')
    w, h = rgb.size
    if w < 640 or h < 360 or w > 8192 or h > 8192:
        raise ValueError('Unexpected screenshot dimensions')
    pixels = rgb.load()
    ylo = round(h * .06)
    yhi = round(h * .78)
    active = set()
    for y in range(ylo, yhi):
        for x in range(w):
            if predicate(*pixels[x, y]):
                active.add(y * w + x)
    components = []
    while active:
        first = active.pop()
        queue = deque((first,))
        area = 0
        xmin, xmax = w, 0
        ymin, ymax = h, 0
        while queue:
            i = queue.popleft()
            x, y = i % w, i // w
            area += 1
            xmin = min(xmin, x)
            xmax = max(xmax, x)
            ymin = min(ymin, y)
            ymax = max(ymax, y)
            for near in (i - w, i + w, i - 1 if x else -1, i + 1 if x + 1 < w else -1):
                if near in active:
                    active.remove(near)
                    queue.append(near)
        width, height = xmax - xmin + 1, ymax - ymin + 1
        if area >= min_area and width >= 6 and height >= 8:
            components.append({'area': area, 'x': xmin, 'y': ymin,
                               'width': width, 'height': height,
                               'cx': (xmin + xmax) / 2, 'cy': (ymin + ymax) / 2})
    return sorted(components, key=lambda c: -c['area'])


def verify_frame(image: Image.Image) -> dict:
    w, h = image.size
    allies = color_components(image, _is_ally)
    enemies = color_components(image, _is_enemy)
    # The synthetic SDL renderer places two allied blue bodies to the left and
    # two opposing red bodies farther right on the isometric grid. The legend
    # sits near the bottom and is explicitly excluded from the component scan.
    selected_a, selected_e = allies[:2], enemies[:2]
    ally_pixels = sum(x['area'] for x in selected_a)
    enemy_pixels = sum(x['area'] for x in selected_e)
    horizontal_order = (bool(selected_a and selected_e) and
                        sum(x['cx'] for x in selected_a) / len(selected_a) + w * .06 <
                        sum(x['cx'] for x in selected_e) / len(selected_e))
    accepted = (len(selected_a) == 2 and len(selected_e) == 2 and
                ally_pixels >= 120 and enemy_pixels >= 120 and horizontal_order)
    return {
        'image_width': w, 'image_height': h,
        'ally_components': len(allies), 'enemy_components': len(enemies),
        'largest_ally_areas': [x['area'] for x in selected_a],
        'largest_enemy_areas': [x['area'] for x in selected_e],
        'two_allies_left_of_two_enemies': horizontal_order,
        'plausible_training_frame': accepted,
        'limitations': ('Image-color smoke only; game may render incorrectly despite a pass. '
                        'Manual screenshot review and input testing remain required.'),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('screenshot', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    with Image.open(a.screenshot) as img:
        verdict = verify_frame(img)
    text = json.dumps(verdict, indent=2) + '\n'
    if a.output:
        a.output.write_text(text, encoding='utf-8')
    print(text, end='')
    if not verdict['plausible_training_frame']:
        raise SystemExit('No convincing two-blue-two-red training frame found')


if __name__ == '__main__':
    main()
