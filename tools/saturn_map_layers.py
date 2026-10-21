#!/usr/bin/env python3
"""Read-only statistical survey of candidate Saturn MAP layers (no asset export)."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
from tools.saturn_iso import SaturnISO
from tools.saturn_map_records import MAP_BYTES, TAIL_START
from tools.saturn_map_survey import read_file_payload, file_family

PITCH_WORDS = 64
# Hypothetical partition of the 173-row region, NOT a decoded game format.
SEGMENTS = (("A", 0, 28), ("B", 28, 28), ("C", 56, 14),
            ("D", 70, 28), ("E", 98, 75))


def words(data: bytes) -> list[int]:
    if len(data) != MAP_BYTES or MAP_BYTES - TAIL_START != 173 * 64 * 2:
        raise ValueError("Expected complete known-size MAP file")
    return [int.from_bytes(data[i:i + 2], "big")
            for i in range(TAIL_START, len(data), 2)]


def subregion(values: list[int], row: int, rows: int) -> list[int]:
    if row < 0 or rows <= 0 or (row + rows) * PITCH_WORDS > len(values):
        raise ValueError("Candidate segment out of bounds")
    return values[row * PITCH_WORDS:(row + rows) * PITCH_WORDS]


def compare_layers(left: list[int], right: list[int]) -> dict:
    if not left or len(left) != len(right):
        raise ValueError("Layers must have equal positive word counts")
    mismatches = sum(bool(a) != bool(b) for a, b in zip(left, right))
    overlap = sum(bool(a) and bool(b) for a, b in zip(left, right))
    same_values = sum(a == b and a != 0 for a, b in zip(left, right))
    return {"mask_equal": mismatches == 0,
            "mask_mismatch_positions": mismatches,
            "overlapping_nonzero": overlap,
            "matching_nonzero_values": same_values}


def profile_map(data: bytes) -> dict:
    values = words(data)
    regions = {name: subregion(values, row, count)
               for name, row, count in SEGMENTS}
    return {"segment_nonzero_counts": {
                name: sum(bool(value) for value in region)
                for name, region in regions.items()},
            "AB": compare_layers(regions["A"], regions["B"]),
            "BD": compare_layers(regions["B"], regions["D"]),
            "AD": compare_layers(regions["A"], regions["D"])}


def summary(profiles: dict[str, dict]) -> dict:
    if not profiles:
        raise ValueError("No map statistics")
    result = {}
    for pair in ("AB", "BD", "AD"):
        result[pair] = {
            "maps_with_identical_occupancy": sum(p[pair]["mask_equal"] for p in profiles.values()),
            "mismatched_positions_total": sum(p[pair]["mask_mismatch_positions"] for p in profiles.values()),
            "overlapping_nonzero_total": sum(p[pair]["overlapping_nonzero"] for p in profiles.values()),
            "matching_nonzero_values_total": sum(p[pair]["matching_nonzero_values"] for p in profiles.values()),
            "exceptions": [name for name in sorted(profiles)
                           if not profiles[name][pair]["mask_equal"]],
        }
    families = {}
    for name, p in profiles.items():
        family = "M_SHOW" if name == "M_SHOW.MAP" else file_family(name)
        row = families.setdefault(family, Counter())
        row["count"] += 1
        row["AB_exact"] += p["AB"]["mask_equal"]
        row["BD_exact"] += p["BD"]["mask_equal"]
    result["families"] = {name: dict(row) for name, row in sorted(families.items())}
    return result


def analyze_disc(iso: SaturnISO) -> dict:
    fs = iso.inspect(include_files=True)
    maps = sorted((entry for entry in fs["file_entries"]
                   if entry["name"].upper().endswith(".MAP")),
                  key=lambda item: item["name"])
    if not maps:
        raise ValueError("No MAP files found")
    profiles = {}
    with iso.path.open("rb") as stream:
        for entry in maps:
            profiles[entry["name"]] = profile_map(read_file_payload(iso, stream, entry))
    return {
        "source_product_code": fs["boot_product_code"],
        "source_volume": fs["volume_id"],
        "map_count": len(profiles),
        "candidate_pitch_words": PITCH_WORDS,
        "candidate_tail_words": 173 * PITCH_WORDS,
        "candidate_segments": [{"name": name, "start_row": row, "rows": count}
                               for name, row, count in SEGMENTS],
        "summary": summary(profiles),
        "maps": profiles,
        "limitations": "Candidate layout, NOT authenticated gameplay geometry. English v1.1 translated disc.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track1", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(analyze_disc(SaturnISO(args.track1)),
                         indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
