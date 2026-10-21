#!/usr/bin/env python3
"""Stage72: compare Python's independent ordered tile digest to actual C++.

Only fabricated manifests from Stage71 are ever created by this tool.
FNV-1a is a deterministic regression checksum, NOT a cryptographic
authentication of any original Saturn media.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

from tools.check_terrain_matrix import CASES, invented_cell, make_case
from tools.saturn_terrain_bridge import export_numeric_terrain

MASK64 = (1 << 64) - 1
RECEIPT = re.compile(r"VH_TERRAIN_ORDER_V1 cells=(\d+) digest=([0-9a-f]{16}) units=(\d+)")


def ordered_digest(width, height, cells):
    """Reference implementation using Python LE byte encoding, not C++ output."""
    state = 14695981039346656037
    for num in (width, height):
        for value in num.to_bytes(4, "little", signed=False):
            state = ((state ^ value) * 1099511628211) & MASK64
    if len(cells) != width * height:
        raise ValueError("incomplete ordered tile stream")
    for i, tile in enumerate(cells):
        if tile["x"] != i % width or tile["y"] != i // width:
            raise ValueError("unordered tile source")
        values = (
            (int(tile["elevation"]) & 0xffffffff).to_bytes(4, "little"),
            int(tile["movement_cost"]).to_bytes(4, "little", signed=False),
            bytes([int(tile["traversable"])]),
        )
        for value_bytes in values:
            for value in value_bytes:
                state = ((state ^ value) * 1099511628211) & MASK64
    return state


def independent_case_digest(w, h):
    return ordered_digest(w, h, [
        invented_cell(x, y, w, h)
        for y in range(h) for x in range(w)
    ])


def swap_fields(text, first_idx, second_idx, fields):
    """Swap tile value fields WITHOUT changing coordinates or aggregate sums."""
    lines = text.splitlines()
    first = lines[2 + first_idx].split()
    second = lines[2 + second_idx].split()
    if first[:1] != ["CELL"] or second[:1] != ["CELL"]:
        raise AssertionError("not a tile row")
    for index in fields:
        first[index], second[index] = second[index], first[index]
    lines[2 + first_idx] = " ".join(first)
    lines[2 + second_idx] = " ".join(second)
    changed = "\n".join(lines) + "\n"
    if changed == text:
        raise AssertionError("mutation did not change fixture")
    return changed


def audit(binary: Path):
    if not binary.is_file():
        raise FileNotFoundError("compiled ordered terrain probe missing")
    confirmed = 0
    with tempfile.TemporaryDirectory(prefix="vh-synthetic-tile-identity-") as folder:
        path = Path(folder) / "fabricated.vhterrain"
        def inspect(text):
            path.write_text(text, encoding="ascii")
            process = subprocess.run(
                [str(binary.resolve()), str(path)],
                capture_output=True, text=True, timeout=25
            )
            if process.returncode != 0 or process.stderr:
                raise AssertionError("native rejected complete invented terrain")
            match = RECEIPT.fullmatch(process.stdout.strip())
            if not match:
                raise AssertionError("unexpected native ordered digest format")
            count, digest_hex, units = match.groups()
            if int(units) != 0:
                raise AssertionError("terrain parser created invented units")
            return int(count), int(digest_hex, 16)

        for width, height in CASES:
            data = export_numeric_terrain(make_case(width, height))
            count, native = inspect(data)
            expected = independent_case_digest(width, height)
            if count != width * height or native != expected:
                raise AssertionError("per-cell ordered C++/Python digest mismatch")
            confirmed += 1

        # Equal sums do not prove equal tile placement. Swapping two distinct
        # complete payloads must change the native ordered checksum.
        w, h = 7, 13
        base = export_numeric_terrain(make_case(w, h))
        _, before = inspect(base)
        source = make_case(w, h)["cells"]
        mutations = [
            (0, 1, (3, 4, 5)),   # full tile payload swap
            (0, 1, (3,)),       # signed elevation swap
            (0, 1, (4,)),       # weighted cost swap
        ]
        blocked_idx = next(i for i, c in enumerate(source) if not c["traversable"])
        mutations.append((0, blocked_idx, (5,)))  # walkability swap
        rejected_equivalent_sums = 0
        for idx_a, idx_b, fields in mutations:
            mutated = swap_fields(base, idx_a, idx_b, fields)
            count, changed = inspect(mutated)
            # The Python reference must also detect each relevant permutation.
            amended = [dict(c) for c in source]
            keys = {3: "elevation", 4: "movement_cost", 5: "traversable"}
            for k in fields:
                key = keys[k]
                amended[idx_a][key], amended[idx_b][key] = (
                    amended[idx_b][key], amended[idx_a][key]
                )
            expected = ordered_digest(w, h, amended)
            if count != w*h or changed != expected or changed == before:
                raise AssertionError("C++ failed equal-sum permutation audit")
            rejected_equivalent_sums += 1

    return {
        "origin": "fabricated_synthetic_only",
        "sizes_verified": confirmed,
        "max_cells_verified": 128*128,
        "equal_sum_tile_permutations_detected": rejected_equivalent_sums,
        "does_not_create_units": True,
        "digest_is_noncryptographic": True,
        "original_saturn_data_authenticated": False,
        "original_first_battle_playable": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(audit(args.binary), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    print(result, end="")


if __name__ == "__main__":
    main()
