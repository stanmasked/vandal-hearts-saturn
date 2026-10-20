#!/usr/bin/env python3
"""Stage 16: map-local A/B codebook ambiguity and spatial permutation controls.

Read an owned Sega Saturn image privately; produce only numeric statistics.
Candidate A/B regions are NOT authenticated game tiles, attributes or graphics.
No source word values, record data, textures, positions or audio are exported.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Mapping

from tools.saturn_map_ab_prediction import decode_ab, PITCH
from tools.saturn_map_ab_blocked import evaluate

PERMUTATIONS = 8
CONTROLS = ("within_row", "whole_map")


def paired_positions(a: list[int], b: list[int]) -> list[int]:
    if not a or len(a) != len(b):
        raise ValueError("Expected aligned 64-word candidate rows")
    if any(not isinstance(v, int) or not 0 <= v <= 65535 for v in a + b):
        raise ValueError("Only BE16 unsigned word values are supported")
    return [i for i, (x, y) in enumerate(zip(a, b)) if x and y]


def ambiguity(a: list[int], b: list[int]) -> dict:
    """Map-local in-sample codebook statistics, NOT a decoded lookup."""
    positions = paired_positions(a, b)
    if not positions:
        return dict(pairs=0, distinct_a=0, distinct_b=0, singleton_target_a=0,
                    ambiguous_target_a=0, deterministic_a_pair_mass=0,
                    modal_correct_in_sample=0, baseline_correct_in_sample=0,
                    conditional_entropy_bits=None, b_entropy_bits=None)
    a_to_b: dict[int, Counter[int]] = defaultdict(Counter)
    b_counts = Counter()
    for i in positions:
        x, y = a[i], b[i]
        a_to_b[x][y] += 1
        b_counts[y] += 1
    n = len(positions)
    def entropy(counts: Counter) -> float:
        total = sum(counts.values())
        return -sum((v / total) * math.log2(v / total) for v in counts.values())
    cond = sum(sum(c.values()) / n * entropy(c) for c in a_to_b.values())
    unique = [c for c in a_to_b.values() if len(c) == 1]
    return {
        "pairs": n,
        "distinct_a": len(a_to_b),
        "distinct_b": len(b_counts),
        "singleton_target_a": len(unique),
        "ambiguous_target_a": len(a_to_b) - len(unique),
        "deterministic_a_pair_mass": sum(sum(c.values()) for c in unique),
        "modal_correct_in_sample": sum(max(c.values()) for c in a_to_b.values()),
        "baseline_correct_in_sample": max(b_counts.values()),
        "conditional_entropy_bits": round(cond, 6),
        "b_entropy_bits": round(entropy(b_counts), 6),
    }


def permute_targets(a: list[int], b: list[int], mode: str, seed: int) -> list[int]:
    """Keep positions and B marginals fixed; randomize B assignments only.

    For within_row controls, preserve each candidate row's B distribution.
    For whole_map controls, preserve total B distribution. All A/B zero
    masks and test pair counts are identical in both controls.
    """
    positions = paired_positions(a, b)
    if mode not in CONTROLS:
        raise ValueError("Unknown shuffle mode")
    rng = random.Random(seed)
    groups: dict[int, list[int]] = defaultdict(list)
    for pos in positions:
        groups[pos // PITCH if mode == "within_row" else 0].append(pos)
    shuffled = list(b)
    for indices in groups.values():
        values = [b[i] for i in indices]
        rng.shuffle(values)
        for pos, value in zip(indices, values):
            shuffled[pos] = value
    return shuffled


def stable_seed(name: str, control: str, repeat: int) -> int:
    if repeat < 0:
        raise ValueError("Negative repetition")
    source = f"vhsaturn-stage16:{name}:{control}:{repeat}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(source).digest()[:8], "big")


def aggregate(samples: Mapping[str, bytes], permutations: int = PERMUTATIONS) -> dict:
    """Use blocked four-fold holdouts on observed and shuffled map-local data."""
    if not samples or permutations < 1 or permutations > 128:
        raise ValueError("Expected samples and 1–128 permutations")
    per_file = {}
    for name, blob in sorted(samples.items()):
        if not name.upper().endswith(".MAP"):
            raise ValueError("Only MAP files supported")
        a, b = decode_ab(blob)
        stats = ambiguity(a, b)
        original = evaluate(a, b, split="blocked")
        controls = {}
        for control in CONTROLS:
            sums = Counter()
            for i in range(permutations):
                permuted = permute_targets(a, b, control, stable_seed(name, control, i))
                if sum(bool(x and y) for x, y in zip(a, permuted)) != stats["pairs"]:
                    raise AssertionError("Control changed occupied test population")
                sums.update(evaluate(a, permuted, split="blocked"))
            controls[control] = dict(sums)
        per_file[name] = {"ambiguity": stats, "observed": original,
                          "shuffled": controls}

    def totals_for(which: str, control: str | None = None) -> dict:
        data = [item[which] if control is None else item[which][control]
                for item in per_file.values()]
        return {key: sum(row[key] for row in data)
                for key in ("covered", "model_correct", "baseline_correct_covered",
                            "test_nonzero", "folds_without_training")}

    observed = totals_for("observed")
    shuffled_totals = {control: totals_for("shuffled", control) for control in CONTROLS}

    def percentages(counts: dict, repetitions: int) -> dict:
        covered = counts["covered"]
        return {"covered_test_pairs": covered,
                "test_nonzero_pairs": counts["test_nonzero"],
                "model_correct": counts["model_correct"],
                "baseline_correct": counts["baseline_correct_covered"],
                "model_accuracy": round(counts["model_correct"] / covered, 6) if covered else None,
                "baseline_accuracy": round(counts["baseline_correct_covered"] / covered, 6) if covered else None,
                "empty_training_folds": counts["folds_without_training"],
                "replications": repetitions}

    ambiguity_totals = {key: sum(item["ambiguity"][key] for item in per_file.values())
                        for key in ("pairs", "distinct_a", "distinct_b",
                                    "singleton_target_a", "ambiguous_target_a",
                                    "deterministic_a_pair_mass", "modal_correct_in_sample",
                                    "baseline_correct_in_sample")}
    return {
        "map_count": len(per_file),
        "permutations_per_control_per_map": permutations,
        "candidate_row_width": PITCH,
        "codebook": ambiguity_totals,
        "blocked_holdout": {"observed": percentages(observed, 1),
                            "controls": {control: percentages(counts, permutations)
                                         for control, counts in shuffled_totals.items()}},
        "maps": per_file,
        "limitations": (
            "In-sample modal fits can overfit. Shuffled controls preserve B frequencies "
            "but not original A/B pairing. Multiple B per A values are not decoded "
            "semantics; this is not a gameplay map, texture or collision converter."
        ),
    }


def analyze_disc(track1: Path, permutations: int = PERMUTATIONS) -> dict:
    from tools.saturn_iso import SaturnISO
    from tools.saturn_map_survey import read_file_payload
    iso = SaturnISO(track1)
    inventory = iso.inspect(include_files=True)
    entries = [e for e in inventory["file_entries"] if e["name"].upper().endswith(".MAP")]
    with iso.path.open("rb") as f:
        maps = {e["name"]: read_file_payload(iso, f, e) for e in entries}
    return {"source_product_code": inventory["boot_product_code"],
            "volume_id": inventory["volume_id"],
            "source": "English v1.1 translation-patched Saturn disc",
            "results": aggregate(maps, permutations)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track1", type=Path, help="Private RAW MODE1/2352 image")
    parser.add_argument("--permutations", type=int, default=PERMUTATIONS)
    parser.add_argument("--output", type=Path, help="Write numeric-only statistics")
    args = parser.parse_args()
    result = json.dumps(analyze_disc(args.track1, args.permutations),
                        indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
