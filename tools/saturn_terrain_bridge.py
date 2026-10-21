#!/usr/bin/env python3
"""Stage68: fail-closed private Stage67 observation-to-native terrain bridge.

Never promotes coordinates to authenticated Sega Saturn data, never generates
unit combat parameters or scripts and never uploads private terrain.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.saturn_battle_coverage import assess_coverage

HEADER = "VH_TERRAIN_UNVERIFIED_V1"
MAX_ELEVATION = 100000
MAX_COST = 100000


def export_numeric_terrain(document):
    audit = assess_coverage(document)
    if not audit["coverage_complete"]:
        raise ValueError("reference coverage incomplete: " +
                         ",".join(audit["blockers"]))
    width = document["scene"]["width"]
    height = document["scene"]["height"]
    by_xy = {(cell["x"], cell["y"]): cell for cell in document["cells"]}
    lines = [HEADER, f"SIZE {width} {height}"]
    for y in range(height):
        for x in range(width):
            cell = by_xy[(x, y)]
            height_value, cost = cell["elevation"], cell["movement_cost"]
            if not (-MAX_ELEVATION <= height_value <= MAX_ELEVATION):
                raise ValueError("terrain elevation outside native bridge range")
            if not (1 <= cost <= MAX_COST):
                raise ValueError("terrain cost outside native bridge range")
            lines.append(f"CELL {x} {y} {height_value} {cost} "
                         f"{int(cell['traversable'])}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Private Stage66 JSON evidence manifest")
    parser.add_argument("--output", type=Path, required=True,
                        help="Local/private .vhterrain output (never commit to GitHub)")
    args = parser.parse_args()
    try:
        document = json.loads(args.manifest.read_text(encoding="utf-8"))
        data = export_numeric_terrain(document)
        if args.output.suffix != ".vhterrain":
            raise ValueError("output must end in .vhterrain")
        args.output.write_text(data, encoding="ascii")
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError,
            ValueError, KeyError) as exc:
        # Never echo original source paths, labels or payload in logs.
        print("TERRAIN_BRIDGE_REJECTED " + type(exc).__name__, file=sys.stderr)
        return 1
    print("TERRAIN_BRIDGE_UNVERIFIED_WRITTEN cells=" +
          str(document["scene"]["width"] * document["scene"]["height"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
