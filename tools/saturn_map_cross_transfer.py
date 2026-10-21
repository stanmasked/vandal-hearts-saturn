#!/usr/bin/env python3
"""Test MAP candidate A/B associations across distinct Saturn scene files.

Leave the target MAP file entirely out of training. Report counts only; original
A/B values never leave local process memory. No tile/graphics semantics assumed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Mapping

from tools.saturn_map_ab_prediction import decode_ab, family_of

SCOPES = ('same_family', 'other_families', 'all_other')
COUNT_KEYS = ('test_nonzero', 'covered', 'model_correct', 'baseline_correct_covered',
              'baseline_correct_all', 'evaluated_maps', 'skipped_maps',
              'skipped_nonzero', 'training_pairs')


def mode(counts: Counter[int]) -> int:
    if not counts:
        raise ValueError('Cannot compute a mode from empty data')
    return max(counts, key=lambda value: (counts[value], -value))


def candidate_pair_counts(blob: bytes) -> Counter[tuple[int, int]]:
    """Nonzero aligned BE16 pairs, only retained privately in memory."""
    a, b = decode_ab(blob)
    return Counter((x, y) for x, y in zip(a, b) if x and y)


def train_test(target: Counter[tuple[int, int]],
               training: Counter[tuple[int, int]]) -> dict[str, int]:
    """Predict B given A with training from different MAPs only.

    No smoothing or fallback: unseen A words are uncovered, not guessed.
    The baseline is estimated from the exact same training file set and
    evaluated on precisely the same covered test pairs.
    """
    if any(v < 0 for v in target.values()) or any(v < 0 for v in training.values()):
        raise ValueError('Negative candidate frequencies')
    test_nonzero = sum(target.values())
    if not training:
        return dict(test_nonzero=0, covered=0, model_correct=0,
                    baseline_correct_covered=0, baseline_correct_all=0,
                    evaluated_maps=0, skipped_maps=1,
                    skipped_nonzero=test_nonzero, training_pairs=0)
    by_a: dict[int, Counter[int]] = defaultdict(Counter)
    base = Counter()
    for (x, y), n in training.items():
        if x == 0 or y == 0 or n <= 0:
            raise ValueError('Training must contain positive frequencies of nonzero words')
        by_a[x][y] += n
        base[y] += n
    predictions = {x: mode(freq) for x, freq in by_a.items()}
    base_prediction = mode(base)
    out = Counter()
    for (x, y), n in target.items():
        if x == 0 or y == 0 or n <= 0:
            raise ValueError('Target must contain positive frequencies of nonzero words')
        out['test_nonzero'] += n
        out['baseline_correct_all'] += n * (base_prediction == y)
        if x in predictions:
            out['covered'] += n
            out['model_correct'] += n * (predictions[x] == y)
            out['baseline_correct_covered'] += n * (base_prediction == y)
    return dict(test_nonzero=out['test_nonzero'], covered=out['covered'],
                model_correct=out['model_correct'],
                baseline_correct_covered=out['baseline_correct_covered'],
                baseline_correct_all=out['baseline_correct_all'],
                evaluated_maps=1, skipped_maps=0, skipped_nonzero=0,
                training_pairs=sum(training.values()))


def rates(counts: dict[str, int]) -> dict[str, float | None]:
    covered, tested = counts['covered'], counts['test_nonzero']
    return {'coverage': round(covered / tested, 6) if tested else None,
            'model_accuracy_covered': round(counts['model_correct'] / covered, 6)
            if covered else None,
            'baseline_accuracy_covered': round(counts['baseline_correct_covered'] / covered, 6)
            if covered else None,
            'baseline_accuracy_all': round(counts['baseline_correct_all'] / tested, 6)
            if tested else None}


def analyze_pairs(samples: Mapping[str, Counter[tuple[int, int]]]) -> dict:
    """Cross-file leave-one-map-out: group and global counters exclude target.

    File contributions are kept as Counters; subtraction guarantees no target
    records appear in same-family and all-other training data.
    """
    if not samples:
        raise ValueError('At least one MAP file is required')
    files = {}
    all_pairs = Counter()
    by_family: dict[str, Counter[tuple[int, int]]] = defaultdict(Counter)
    for name, pairs in samples.items():
        if not name.upper().endswith('.MAP'):
            raise ValueError('Unexpected non-MAP sample')
        if any(n <= 0 or x == 0 or y == 0 for (x, y), n in pairs.items()):
            raise ValueError('Source pairs must be nonzero and have positive frequency')
        family = family_of(name)
        all_pairs.update(pairs)
        by_family[family].update(pairs)
    for name, sample_pairs in sorted(samples.items()):
        family = family_of(name)
        training_by_scope = {
            'same_family': by_family[family] - sample_pairs,
            'other_families': all_pairs - by_family[family],
            'all_other': all_pairs - sample_pairs,
        }
        files[name] = {'family': family,
                       'results': {scope: train_test(sample_pairs, pairs)
                                   for scope, pairs in training_by_scope.items()}}
    aggregates = {}
    for scope in SCOPES:
        values = [f['results'][scope] for f in files.values()]
        totals = {key: sum(value[key] for value in values) for key in COUNT_KEYS}
        aggregates[scope] = {'counts': totals, 'rates': rates(totals)}
    by_family_summary = {}
    for family in sorted(by_family):
        group = [f for f in files.values() if f['family'] == family]
        for scope in SCOPES:
            values = [f['results'][scope] for f in group]
            totals = {key: sum(value[key] for value in values) for key in COUNT_KEYS}
            by_family_summary.setdefault(family, {})[scope] = {
                'maps_in_family': len(group), 'counts': totals, 'rates': rates(totals)}
    return {
        'map_count': len(files), 'scopes': list(SCOPES),
        'overall': aggregates, 'by_family': by_family_summary, 'maps': files,
        'validation': 'leave-one-whole-map-out; candidate value modes have no target-map exposure',
        'limitations': ('A/B arrays have not been identified as terrain or graphics. '
                        'Comparisons have different training sets and coverage; '
                        'singleton-family MAPs have no same-family training. '
                        'No copyrighted words or texture bytes are exported.'),
    }


def analyze_samples(samples: Mapping[str, bytes]) -> dict:
    if not samples:
        raise ValueError('No MAP samples')
    return analyze_pairs({name: candidate_pair_counts(blob) for name, blob in samples.items()})


def analyze_disc(track1: Path) -> dict:
    from tools.saturn_iso import SaturnISO
    from tools.saturn_map_survey import read_file_payload
    iso = SaturnISO(track1)
    fs = iso.inspect(include_files=True)
    maps = [entry for entry in fs['file_entries'] if entry['name'].upper().endswith('.MAP')]
    with iso.path.open('rb') as stream:
        samples = {entry['name']: read_file_payload(iso, stream, entry) for entry in maps}
    return {'product_code': fs['boot_product_code'],
            'volume_id': fs['volume_id'],
            'source_note': 'English v1.1 translation-patched Saturn release',
            'results': analyze_samples(samples)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('track1', type=Path)
    parser.add_argument('--output', type=Path, help='Count-only JSON (not media)')
    args = parser.parse_args()
    report = json.dumps(analyze_disc(args.track1), indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    else:
        print(report, end='')


if __name__ == '__main__':
    main()
