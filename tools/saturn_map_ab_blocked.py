#!/usr/bin/env python3
"""Stage 14: blocked vs interleaved, spatial negative controls for MAP A/B.

Works on privately held Saturn RAW MODE1/2352 data, exporting only counts,
percentages and original filenames. A/B are UNVERIFIED structural candidates,
not decoded graphics, map tiles, heights or gameplay geometry.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Mapping

from tools.saturn_map_ab_prediction import decode_ab, PITCH


def mode(counter: Counter[int]) -> int:
    if not counter:
        raise ValueError("Cannot compute mode of empty training data")
    return max(counter, key=lambda value: (counter[value], -value))

ROWS = 28
FOLDS = 4
SHIFTS = (0, 1, 64, 448, 896)
SPLITS = ('interleaved', 'blocked')
COUNT_KEYS = (
    'test_nonzero', 'covered', 'model_correct', 'baseline_correct_covered',
    'baseline_correct_all', 'folds_without_training',
)


def fold_for_row(row: int, folds: int, rows: int, split: str) -> int:
    """Return an integer fold; contiguous blocks use exactly even-sized chunks."""
    if row < 0 or row >= rows or folds < 2 or folds > rows:
        raise ValueError('Invalid fold/row selection')
    if split == 'interleaved':
        return row % folds
    if split == 'blocked':
        return (row * folds) // rows
    raise ValueError('Unknown row holdout scheme')


def evaluate(a: list[int], b: list[int], split: str = 'blocked',
             shift: int = 0, folds: int = FOLDS) -> dict[str, int]:
    """Cross-validated model/B-mode comparison with no heldout-row leakage.

    The shifted controls rotate target words, not input words. Test positions
    are counted only when A and shifted B are nonzero. All reported accuracies
    are based on the SAME covered positions for model vs constant baseline.
    Folds with no training pairs are explicitly marked skipped.
    """
    if not a or len(a) != len(b) or len(a) % PITCH:
        raise ValueError('Equal nonempty complete row arrays required')
    rows = len(a) // PITCH
    if folds < 2 or folds > rows or not 0 <= shift < len(b):
        raise ValueError('Invalid number of folds or shift')
    if split not in SPLITS:
        raise ValueError('Invalid holdout split')
    if any(not isinstance(v, int) or not 0 <= v <= 65535 for v in a + b):
        raise ValueError('Only unsigned 16-bit word values accepted')
    shifted = b[shift:] + b[:shift] if shift else b
    counts = Counter()
    row_folds = [fold_for_row(row, folds, rows, split) for row in range(rows)]
    for excluded in range(folds):
        lookup: dict[int, Counter[int]] = defaultdict(Counter)
        baseline: Counter[int] = Counter()
        for i, (x, y) in enumerate(zip(a, shifted)):
            if x and y and row_folds[i // PITCH] != excluded:
                lookup[x][y] += 1
                baseline[y] += 1
        if not baseline:
            counts['folds_without_training'] += 1
            continue
        guesses = {x: mode(by_y) for x, by_y in lookup.items()}
        modal_target = mode(baseline)
        for i, (x, y) in enumerate(zip(a, shifted)):
            if not x or not y or row_folds[i // PITCH] != excluded:
                continue
            counts['test_nonzero'] += 1
            counts['baseline_correct_all'] += (y == modal_target)
            if x in guesses:
                counts['covered'] += 1
                counts['model_correct'] += (y == guesses[x])
                counts['baseline_correct_covered'] += (y == modal_target)
    return {key: counts[key] for key in COUNT_KEYS}


def rates(counts: Mapping[str, int]) -> dict[str, float | None]:
    covered, total = counts['covered'], counts['test_nonzero']
    return {
        'fraction_covered': round(covered / total, 6) if total else None,
        'model_accuracy_covered': round(counts['model_correct'] / covered, 6) if covered else None,
        'baseline_accuracy_covered': round(counts['baseline_correct_covered'] / covered, 6) if covered else None,
        'fraction_tested_of_possible': None,  # A/B occupancy can change with shift.
    }


def analyze_samples(samples: Mapping[str, bytes]) -> dict:
    if not samples:
        raise ValueError('No MAP samples')
    per_map = {}
    for name, blob in sorted(samples.items()):
        if not name.upper().endswith('.MAP'):
            raise ValueError('Unexpected file type')
        a, b = decode_ab(blob)
        per_map[name] = {split: {str(shift): evaluate(a, b, split, shift)
                                for shift in SHIFTS} for split in SPLITS}
    aggregated = {}
    for split in SPLITS:
        aggregated[split] = {}
        for shift in SHIFTS:
            c = {key: sum(report[split][str(shift)][key] for report in per_map.values())
                 for key in COUNT_KEYS}
            aggregated[split][str(shift)] = {'counts': c, 'rates': rates(c)}
    return {
        'source_file_count': len(per_map),
        'candidate_rows': ROWS, 'candidate_pitch_words': PITCH,
        'holdout_schemes': list(SPLITS), 'folds': FOLDS,
        'shift_controls_words': list(SHIFTS),
        'aggregate': aggregated, 'files': per_map,
        'limitations': (
            'Candidate layers are not authenticated Saturn game geometry. '
            'Fold skips reduce tested samples; shifted conditions differ in '
            'nonzero positions. Numeric accuracy alone cannot identify the '
            'underlying records as tiles, art, heights or collision data.'
        ),
    }


def analyze_disc(track1: Path) -> dict:
    from tools.saturn_iso import SaturnISO
    from tools.saturn_map_survey import read_file_payload
    iso = SaturnISO(track1)
    fs = iso.inspect(include_files=True)
    entries = [e for e in fs['file_entries'] if e['name'].upper().endswith('.MAP')]
    with iso.path.open('rb') as stream:
        samples = {entry['name']: read_file_payload(iso, stream, entry)
                   for entry in entries}
    return {
        'product_code': fs['boot_product_code'],
        'source_volume_id': fs['volume_id'],
        'source_note': 'User-owned English v1.1 translation-patched Saturn disc',
        'results': analyze_samples(samples),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('track1', type=Path, help='Private Saturn Track 1 RAW BIN')
    parser.add_argument('--output', type=Path, help='Write numeric-only JSON report')
    args = parser.parse_args()
    report = json.dumps(analyze_disc(args.track1), indent=2,
                        ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    else:
        print(report, end='')


if __name__ == '__main__':
    main()
