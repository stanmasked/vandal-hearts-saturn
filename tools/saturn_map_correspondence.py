#!/usr/bin/env python3
"""Stage 11: MAP field/layer association and unambiguous ordering anchors.

Only numeric aggregates are serialized; original game values and candidate
positions remain in private process memory. This is NOT a map decoder.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from tools.saturn_iso import SaturnISO
from tools.saturn_map_layers import SEGMENTS, PITCH_WORDS
from tools.saturn_map_records import MAP_BYTES, TAIL_START, decode_record_table
from tools.saturn_map_survey import read_file_payload

FIELD_COUNT = 6


def candidate_data(blob: bytes) -> tuple[list[tuple[int, ...]], dict[str, list[int]]]:
    """Parse candidate records and candidate BE16 tail regions (not geometry)."""
    if len(blob) != MAP_BYTES:
        raise ValueError("Wrong MAP length")
    records = decode_record_table(blob)
    if not records:
        raise ValueError("Expected nonempty candidate record prefix")
    word_values = [int.from_bytes(blob[i:i + 2], "big")
                   for i in range(TAIL_START, MAP_BYTES, 2)]
    if len(word_values) != sum(rows for _, _, rows in SEGMENTS) * PITCH_WORDS:
        raise ValueError("Candidate tail size mismatch")
    regions = {name: word_values[row * PITCH_WORDS:(row + rows) * PITCH_WORDS]
               for name, row, rows in SEGMENTS}
    return records, regions


def multiset_match_table(records: list[tuple[int, ...]],
                         regions: dict[str, list[int]]) -> tuple[dict[str, list[int]], dict[str, int]]:
    """Intersection sizes ONLY; never expose private counter keys."""
    if not records or any(len(row) != FIELD_COUNT for row in records):
        raise ValueError("Candidate records must have six fields")
    if not regions:
        raise ValueError("No candidate regions")
    field_counts = [Counter(record[field] for record in records)
                    for field in range(FIELD_COUNT)]
    table, nonzero_counts = {}, {}
    for name, values in regions.items():
        if not values:
            raise ValueError("Empty candidate region")
        word_counts = Counter(value for value in values if value)
        nonzero_counts[name] = sum(word_counts.values())
        table[name] = [sum((word_counts & counter).values()) for counter in field_counts]
    return table, nonzero_counts


def unique_anchor_order(records: list[tuple[int, ...]], layer: list[int],
                        record_field: int = 1) -> dict:
    """Count ordered anchors unique in both lists; never assign duplicates."""
    if not records or not 0 <= record_field < FIELD_COUNT or not layer:
        raise ValueError("Invalid anchor inputs")
    if any(len(row) != FIELD_COUNT for row in records):
        raise ValueError("Records must have six fields")
    record_values = [row[record_field] for row in records]
    record_counts = Counter(record_values)
    layer_counts = Counter(value for value in layer if value)
    private_unique_indices = {value: index for index, value in enumerate(record_values)
                              if record_counts[value] == 1}
    private_anchors = [(position, private_unique_indices[value])
                       for position, value in enumerate(layer)
                       if value != 0 and layer_counts[value] == 1
                       and value in private_unique_indices]
    rising = sum(nxt > previous
                 for (_, previous), (_, nxt) in zip(private_anchors, private_anchors[1:]))
    falling = sum(nxt < previous
                  for (_, previous), (_, nxt) in zip(private_anchors, private_anchors[1:]))
    return {"unambiguous_anchors": len(private_anchors),
            "adjacent_ascending": rising, "adjacent_descending": falling,
            "adjacent_comparisons": max(0, len(private_anchors) - 1)}


def analyze_samples(samples: dict[str, bytes]) -> dict:
    if not samples:
        raise ValueError("No MAP files")
    names = [name for name, _, _ in SEGMENTS]
    totals = {name: [0] * FIELD_COUNT for name in names}
    nonzeros = {name: 0 for name in names}
    anchor_total = ups = downs = enough = insufficient = 0
    per_file = {}
    for name in sorted(samples):
        if not name.upper().endswith(".MAP"):
            raise ValueError("Non-MAP input file")
        records, regions = candidate_data(samples[name])
        matches, counts = multiset_match_table(records, regions)
        anchors = unique_anchor_order(records, regions["A"])
        for section in names:
            nonzeros[section] += counts[section]
            for field in range(FIELD_COUNT):
                totals[section][field] += matches[section][field]
        anchor_total += anchors["unambiguous_anchors"]
        ups += anchors["adjacent_ascending"]
        downs += anchors["adjacent_descending"]
        enough += anchors["unambiguous_anchors"] >= 2
        insufficient += anchors["unambiguous_anchors"] < 2
        per_file[name] = {"active_candidate_records": len(records),
                          "layer_a_nonzero": counts["A"],
                          "a_word_1_matches_multiset": matches["A"][1], **anchors}
    return {
        "map_count": len(per_file),
        "method": "BE16 multiset overlap and unique-value order; not decoded geometry",
        "region_words": {name: rows * PITCH_WORDS for name, _, rows in SEGMENTS},
        "field_indices": list(range(FIELD_COUNT)),
        "nonzero_word_counts": nonzeros,
        "matches_by_region_and_record_field": totals,
        "a_field_1_overlap_fraction": round(totals["A"][1] / nonzeros["A"], 6)
        if nonzeros["A"] else None,
        "unambiguous_anchor_count": anchor_total,
        "maps_with_two_or_more_anchors": enough,
        "maps_with_fewer_than_two_anchors": insufficient,
        "anchor_adjacent_ascending": ups, "anchor_adjacent_descending": downs,
        "anchor_ascending_fraction": round(ups / (ups + downs), 6) if ups + downs else None,
        "maps": per_file,
        "limitations": ("Candidate regions not verified as geometry. Shared order may reflect "
                        "resource indexing; duplicated values have no unique position. "
                        "No original game data exported."),
    }


def analyze_disc(path: Path) -> dict:
    iso = SaturnISO(path)
    fs = iso.inspect(include_files=True)
    maps = [entry for entry in fs["file_entries"] if entry["name"].upper().endswith(".MAP")]
    with iso.path.open("rb") as stream:
        samples = {e["name"]: read_file_payload(iso, stream, e) for e in maps}
    return {"product_code": fs["boot_product_code"],
            "source_volume": fs["volume_id"],
            "result": analyze_samples(samples),
            "source_note": "English v1.1 translation-patched; original Japanese data not verified."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track1", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(analyze_disc(args.track1), indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
