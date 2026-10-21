#!/usr/bin/env python3
"""Stage71: multi-size synthetic Stage66/67/68 -> actual compiled C++ importer.

All grids are deterministic fabricated numbers; never reads Saturn tracks,
extracts map data, or outputs user-supplied private records.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from tools.check_terrain_bridge import synthetic_manifest, parse_receipt
from tools.saturn_terrain_bridge import export_numeric_terrain

CASES = ((2, 2), (3, 5), (7, 13), (17, 9), (1, 128), (128, 1), (128, 128))


def invented_cell(x: int, y: int, w: int, h: int) -> dict:
    # Signed relative heights, weighted paths and impassable tiles are all
    # present in generated fixtures, including the 128x128 native maximum.
    terminal = (x == 0 and y == 0) or (x == w - 1 and y == h - 1)
    return {
        "x": x, "y": y, "terrain": "fictional_grid_cell",
        "elevation": ((13 * x + 23 * y) % 19) - 9,
        "movement_cost": 1 + ((7 * x + 11 * y) % 17),
        "traversable": terminal or (x * 5 + y * 3) % 7 != 0,
        "confidence": "observed", "evidence_ids": ["local-fixture"],
    }


def make_case(width: int, height: int) -> dict:
    if not (1 <= width <= 128 and 1 <= height <= 128) or width * height < 2:
        raise ValueError("unsupported synthetic grid size")
    result = synthetic_manifest()
    result["scene"]["width"] = width
    result["scene"]["height"] = height
    result["cells"] = [
        invented_cell(x, y, width, height)
        for y in range(height) for x in range(width)
    ]
    result["units"][1]["x"] = width - 1
    result["units"][1]["y"] = height - 1
    result["turns"][0]["actions"][0]["to"] = (
        {"x": 1, "y": 0} if width > 1 else {"x": 0, "y": 1}
    )
    return result


def independent_aggregates(width: int, height: int):
    total_walk = total_cost = total_elev = 0
    for y in range(height):
        for x in range(width):
            cell = invented_cell(x, y, width, height)
            total_walk += int(cell["traversable"])
            total_cost += cell["movement_cost"]
            total_elev += cell["elevation"]
    total = width * height
    return (width, height, total, total_walk, total - total_walk,
            total_cost, total_elev, 0)


def check(binary: Path):
    if not binary.is_file():
        raise FileNotFoundError("compiled terrain probe missing")
    results = []
    with tempfile.TemporaryDirectory(prefix="vh-synthetic-size-grid-") as td:
        path = Path(td) / "generated.vhterrain"

        def run_native(data: str, should_pass: bool):
            path.write_text(data, encoding="ascii")
            process = subprocess.run(
                [str(binary.resolve()), str(path)], capture_output=True,
                text=True, timeout=20,
            )
            if should_pass:
                if process.returncode != 0 or process.stderr:
                    raise AssertionError("native parser rejected valid synthetic grid")
                return parse_receipt(process.stdout)
            if (process.returncode == 0 or process.stdout.strip()
                    or process.stderr.strip() != "TERRAIN_PROBE_REJECTED"):
                raise AssertionError("native parser accepted malformed grid")
            return None

        for w, h in CASES:
            doc = make_case(w, h)
            data = export_numeric_terrain(doc)
            found = run_native(data, True)
            expected = independent_aggregates(w, h)
            if found != expected:
                raise AssertionError("independent grid aggregates disagree")
            results.append({"size": f"{w}x{h}", "cells": w * h,
                            "negative_height_present": any(
                                c["elevation"] < 0 for c in doc["cells"])})

        max_case = export_numeric_terrain(make_case(128, 128))
        run_native(max_case.replace("SIZE 128 128", "SIZE 129 128", 1), False)
        run_native(max_case.rsplit("CELL ", 1)[0], False)

        invalid_elevation = make_case(3, 5)
        invalid_elevation["cells"][1]["elevation"] = 100001
        try:
            export_numeric_terrain(invalid_elevation)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid elevation was exported")

    return {
        "origin": "deterministic_synthetic_only",
        "tested_sizes": results,
        "complete_roundtrips": len(results),
        "largest_map_cells": max(w*h for w,h in CASES),
        "oversize_grid_rejected": True,
        "truncated_grid_rejected": True,
        "export_range_guard": True,
        "generated_native_units": False,
        "original_Saturn_data": False,
        "original_first_battle_verified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(check(args.binary), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    print(result, end="")


if __name__ == "__main__":
    sys.exit(main())
