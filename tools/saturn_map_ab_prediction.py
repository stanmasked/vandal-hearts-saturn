#!/usr/bin/env python3
"""Stage 13: numeric-only, row-held-out candidate Saturn MAP A/B prediction.

Privately inspect a user-owned RAW MODE1/2352 image. No original record values,
graphics, sprites or map bytes are serialized. No terrain semantics are claimed.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

MAP_BYTES = 170624
TAIL_START = 0x24400
PITCH = 64
ROWS = 28
LAYER_WORDS = PITCH * ROWS
SHIFTS = (0, 1, 64, 65)
FOLDS = 4


def decode_ab(blob: bytes) -> tuple[list[int], list[int]]:
    if len(blob) != MAP_BYTES:
        raise ValueError("Unsupported MAP size")
    end = TAIL_START + LAYER_WORDS * 4
    if end > len(blob):
        raise ValueError("Candidate regions exceed MAP bounds")
    values = [int.from_bytes(blob[at:at + 2], "big")
              for at in range(TAIL_START, end, 2)]
    return values[:LAYER_WORDS], values[LAYER_WORDS:]


def mode(counter: Counter[int]) -> int:
    if not counter:
        raise ValueError("Cannot compute mode of empty training data")
    return max(counter, key=lambda value: (counter[value], -value))


def evaluate(a: list[int], b: list[int], shift: int = 0,
             folds: int = FOLDS) -> dict[str, int]:
    """Row-held-out prediction and training-only modal baseline.

    The candidate arrays are split into disjoint row folds (row index modulo
    folds). The model learns B from A only in other folds. A values absent in
    training are uncovered, not counted as a wrong or a lucky prediction.
    """
    if not a or len(a) != len(b) or len(a) % PITCH:
        raise ValueError("Equal nonempty full rows are required")
    if folds < 2 or folds > len(a) // PITCH or shift < 0 or shift >= len(b):
        raise ValueError("Invalid folds or shift")
    if any(not isinstance(v, int) or v < 0 or v > 65535 for v in a + b):
        raise ValueError("Expected unsigned BE16 values")
    target = b[shift:] + b[:shift] if shift else b
    total = Counter()
    for fold in range(folds):
        counts: dict[int, Counter[int]] = defaultdict(Counter)
        baseline: Counter[int] = Counter()
        for i, (x, y) in enumerate(zip(a, target)):
            if x and y and (i // PITCH) % folds != fold:
                counts[x][y] += 1
                baseline[y] += 1
        if not baseline:
            total["folds_without_training"] += 1
            continue
        guesses = {x: mode(words) for x, words in counts.items()}
        constant_guess = mode(baseline)
        for i, (x, y) in enumerate(zip(a, target)):
            if not x or not y or (i // PITCH) % folds != fold:
                continue
            total["test_nonzero"] += 1
            total["baseline_correct_all"] += (constant_guess == y)
            if x in guesses:
                total["covered"] += 1
                total["model_correct"] += (guesses[x] == y)
                total["baseline_correct_covered"] += (constant_guess == y)
    return {k: total[k] for k in (
        "test_nonzero", "covered", "model_correct",
        "baseline_correct_covered", "baseline_correct_all",
        "folds_without_training"
    )}


def rates(counts: dict[str, int]) -> dict[str, float | None]:
    covered = counts["covered"]
    n = counts["test_nonzero"]
    return {
        "coverage_fraction": round(covered / n, 6) if n else None,
        "model_accuracy_on_covered": round(counts["model_correct"] / covered, 6)
        if covered else None,
        "baseline_accuracy_on_covered": round(counts["baseline_correct_covered"] / covered, 6)
        if covered else None,
        "baseline_accuracy_all": round(counts["baseline_correct_all"] / n, 6)
        if n else None,
    }


def family_of(name: str) -> str:
    if name == "M_SHOW.MAP":
        return "M_SHOW"
    for prefix in ("M_MAP", "M_IVE", "M_KEY"):
        if name.startswith(prefix) and name.endswith(".MAP"):
            return prefix
    return "OTHER"


def sum_rows(results: list[dict[str, int]]) -> dict[str, int]:
    if not results:
        raise ValueError("No report rows")
    return {name: sum(row[name] for row in results) for name in results[0]}


def analyze_samples(samples: dict[str, bytes]) -> dict:
    if not samples:
        raise ValueError("No MAP samples")
    per_file = {}
    for name, blob in sorted(samples.items()):
        if not name.upper().endswith(".MAP"):
            raise ValueError("Non-MAP input")
        a, b = decode_ab(blob)
        per_file[name] = {
            "family": family_of(name),
            "shifts": {str(s): evaluate(a, b, s) for s in SHIFTS},
        }
    all_shifts = {}
    for shift in SHIFTS:
        c = sum_rows([row["shifts"][str(shift)] for row in per_file.values()])
        all_shifts[str(shift)] = {"counts": c, "rates": rates(c)}
    by_family = {}
    for family in sorted({row["family"] for row in per_file.values()}):
        group = [row for row in per_file.values() if row["family"] == family]
        c = sum_rows([row["shifts"]["0"] for row in group])
        by_family[family] = {"maps": len(group), "counts": c, "rates": rates(c)}
    return {
        "map_count": len(per_file),
        "candidate_pitch": PITCH,
        "candidate_layer_rows": ROWS,
        "folds": FOLDS,
        "shift_controls": list(SHIFTS),
        "method": "hold out rows by row index mod 4; train B mode per A value",
        "by_shift": all_shifts,
        "by_family_unshifted": by_family,
        "maps": per_file,
        "limitations": "Candidate A/B are not validated gameplay layers. No source word values exported.",
    }


def analyze_disc(path: Path) -> dict:
    from tools.saturn_iso import SaturnISO
    from tools.saturn_map_survey import read_file_payload
    iso = SaturnISO(path)
    filesystem = iso.inspect(include_files=True)
    entries = [e for e in filesystem["file_entries"]
               if e["name"].upper().endswith(".MAP")]
    with iso.path.open("rb") as stream:
        samples = {e["name"]: read_file_payload(iso, stream, e) for e in entries}
    return {
        "product_code": filesystem["boot_product_code"],
        "source_volume": filesystem["volume_id"],
        "source_note": "English v1.1 translation-patched Saturn release",
        "results": analyze_samples(samples),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track1", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = json.dumps(analyze_disc(args.track1), indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
