#!/usr/bin/env python3
"""Stage 12: test monotone-order hypothesis and duplicate ambiguity in MAP values.

Reads local Saturn media only. Writes aggregate counts, never original values,
record indices, tile positions, graphics, or scripts. Candidate order is
NOT validated gameplay geometry, and conditional matches are NOT decoded cells.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
import json
from pathlib import Path

from tools.saturn_iso import SaturnISO
from tools.saturn_map_correspondence import candidate_data
from tools.saturn_map_survey import read_file_payload


def _validated_words(words: list[int]) -> None:
    if not words or any(not isinstance(v, int) or not 0 <= v <= 65535 for v in words):
        raise ValueError("Expected a nonempty sequence of unsigned 16-bit values")


def unique_value_anchors(records: list[int], layer: list[int]) -> list[tuple[int, int]]:
    """Position pairs unique in both sequences, private in-memory only."""
    _validated_words(records)
    _validated_words(layer)
    record_frequency = Counter(records)
    layer_frequency = Counter(v for v in layer if v)
    unique_record_locations = {v: i for i, v in enumerate(records)
                               if v and record_frequency[v] == 1}
    return [(pos, unique_record_locations[value]) for pos, value in enumerate(layer)
            if value and layer_frequency[value] == 1 and value in unique_record_locations]


def longest_increasing_anchors(anchors: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Maximum-cardinality strictly increasing chain in record index order.

    Input must be sorted by layer position. LIS is a *diagnostic* that may
    DISCARD genuine unique-value pairs, falsifying a simple global mapping.
    """
    if any(a < 0 or b < 0 for a, b in anchors):
        raise ValueError("Negative anchor index")
    if any(x[0] >= y[0] for x, y in zip(anchors, anchors[1:])):
        raise ValueError("Anchor positions must be strictly increasing")
    if len(set(record for _, record in anchors)) != len(anchors):
        raise ValueError("Anchor record positions must be unique")
    if not anchors:
        return []
    tails: list[int] = []
    tail_indices: list[int] = []
    parents = [-1] * len(anchors)
    for i, (_, record_position) in enumerate(anchors):
        k = bisect_left(tails, record_position)
        if k == len(tails):
            tails.append(record_position)
            tail_indices.append(i)
        else:
            tails[k] = record_position
            tail_indices[k] = i
        if k:
            parents[i] = tail_indices[k - 1]
    result = []
    cursor = tail_indices[-1]
    while cursor >= 0:
        result.append(anchors[cursor])
        cursor = parents[cursor]
    return result[::-1]


def sequence_diagnostics(records: list[int], layer: list[int]) -> dict:
    """Count unresolved duplication and conditional candidates; no assignments.

    Assumption for *conditional* candidates: record positions advance with layer
    positions after retaining one LIS of unique anchors. This hypothesis is
    contradicted wherever the LIS omits otherwise unique anchor matches.
    """
    _validated_words(records)
    _validated_words(layer)
    record_positions: dict[int, list[int]] = defaultdict(list)
    for i, value in enumerate(records):
        if value:
            record_positions[value].append(i)
    total = missing = singleton = ambiguous = 0
    for value in layer:
        if not value:
            continue
        total += 1
        n = len(record_positions[value])
        if n == 0:
            missing += 1
        elif n == 1:
            singleton += 1
        else:
            ambiguous += 1
    anchors = unique_value_anchors(records, layer)
    chain = longest_increasing_anchors(anchors)
    endpoints = [(-1, -1)] + chain + [(len(layer), len(records))]
    conditional = conflicts = collision_free = questionable_intervals = 0
    for (lo_layer, lo_record), (hi_layer, hi_record) in zip(endpoints, endpoints[1:]):
        if any(lo_layer < p < hi_layer and not lo_record < r < hi_record
               for p, r in anchors):
            questionable_intervals += 1
        record_hits: Counter[int] = Counter()
        for layer_pos in range(lo_layer + 1, hi_layer):
            val = layer[layer_pos]
            candidate_indices = record_positions[val]
            if not val or len(candidate_indices) <= 1:
                continue
            left = bisect_right(candidate_indices, lo_record)
            right = bisect_left(candidate_indices, hi_record)
            if right - left == 1:
                conditional += 1
                record_hits[candidate_indices[left]] += 1
        for uses in record_hits.values():
            if uses == 1:
                collision_free += 1
            else:
                conflicts += uses
    return {
        "layer_nonzero": total,
        "no_equal_record_value": missing,
        "single_record_candidate": singleton,
        "multiple_record_candidates": ambiguous,
        "unique_in_both_anchors": len(anchors),
        "max_increasing_anchor_chain": len(chain),
        "anchors_excluded_by_monotone_chain": len(anchors) - len(chain),
        "global_monotone_anchor_hypothesis_contradicted": len(chain) != len(anchors),
        "hypothetical_single_candidate_duplicates": conditional,
        "conditional_collision_free_positions": collision_free,
        "conditional_record_collision_positions": conflicts,
        "intervals_with_excluded_anchor_conflicts": questionable_intervals,
    }


def analyze_samples(samples: dict[str, bytes]) -> dict:
    """Whole-disc report: no source values or index sequences serialized."""
    if not samples:
        raise ValueError("At least one MAP must be supplied")
    profiles = {}
    for name in sorted(samples):
        if not name.upper().endswith(".MAP"):
            raise ValueError("Only MAP files are expected")
        records, layers = candidate_data(samples[name])
        profiles[name] = sequence_diagnostics([row[1] for row in records], layers["A"])
    keys = ("layer_nonzero", "no_equal_record_value", "single_record_candidate",
            "multiple_record_candidates", "unique_in_both_anchors",
            "max_increasing_anchor_chain", "anchors_excluded_by_monotone_chain",
            "hypothetical_single_candidate_duplicates", "conditional_collision_free_positions",
            "conditional_record_collision_positions", "intervals_with_excluded_anchor_conflicts")
    totals = {key: sum(p[key] for p in profiles.values()) for key in keys}
    totals.update({
        "map_count": len(profiles),
        "maps_with_unique_anchors": sum(p["unique_in_both_anchors"] > 0 for p in profiles.values()),
        "maps_with_any_anchor_order_contradiction": sum(
            p["global_monotone_anchor_hypothesis_contradicted"] for p in profiles.values()),
        "maps_with_conditional_candidates": sum(
            p["hypothetical_single_candidate_duplicates"] > 0 for p in profiles.values()),
    })
    return {
        "summary": totals,
        "maps": profiles,
        "limitations": (
            "The longest increasing chain is only a conditional test of the assumption "
            "that candidate A positions and 12-byte record indices share one global "
            "increasing order. Excluded anchors contradict that assumption. "
            "Conditionally narrowed duplicates are NOT authenticated mappings "
            "and MUST NOT be exported as tile coordinates or game assets."
        ),
    }


def analyze_disc(track1: Path) -> dict:
    iso = SaturnISO(track1)
    fs = iso.inspect(include_files=True)
    entries = [item for item in fs["file_entries"] if item["name"].upper().endswith(".MAP")]
    with iso.path.open("rb") as handle:
        blobs = {item["name"]: read_file_payload(iso, handle, item) for item in entries}
    return {"product_code": fs["boot_product_code"], "volume_id": fs["volume_id"],
            "source_note": "Translated/modified English v1.1, not verified unmodified Japanese master",
            "result": analyze_samples(blobs)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track1", type=Path, help="User-owned local Saturn RAW MODE1 track")
    parser.add_argument("--output", type=Path, help="Write count-only report outside GitHub")
    args = parser.parse_args()
    payload = json.dumps(analyze_disc(args.track1), indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
