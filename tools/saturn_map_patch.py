#!/usr/bin/env python3
"""Numerical-only checks for correlated changes in Sega Saturn MAP sections.

Process a lawfully obtained RAW MODE1/2352 Saturn track locally; emit only
counts and candidate stride statistics, never game records or textures.
Candidate records and the tail are NOT yet identified as game map geometry.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from tools.saturn_iso import SaturnISO
from tools.saturn_map_records import START, TAIL_START, decode_record_table
from tools.saturn_map_survey import read_file_payload


def difference_pairs(a: bytes, b: bytes, offset: int, stride: int, count: int) -> list[tuple[int, tuple[int, int]]]:
    """Private in-memory word differences (index, before/after). Never export pairs."""
    if len(a) != len(b) or stride < 2 or count < 0 or offset < 0 or offset + count * stride > len(a):
        raise ValueError('Invalid word field region')
    changes = []
    for index in range(count):
        at = offset + index * stride
        before = int.from_bytes(a[at:at + 2], 'big')
        after = int.from_bytes(b[at:at + 2], 'big')
        if before != after:
            changes.append((index, (before, after)))
    return changes


def candidate_stride(indices: list[int], min_lag: int = 16, max_lag: int = 96) -> dict:
    """Choose the strongest repeat lag; this is not proof of a grid pitch."""
    if min_lag < 1 or max_lag < min_lag:
        raise ValueError('Invalid lag bounds')
    if len(indices) != len(set(indices)) or any(i < 0 for i in indices):
        raise ValueError('Indices must be unique nonnegative positions')
    present = set(indices)
    scores = [(lag, sum((pos + lag) in present for pos in present))
              for lag in range(min_lag, max_lag + 1)]
    best_lag, pairs = max(scores, key=lambda row: (row[1], -row[0]))
    return {'candidate_lag': best_lag, 'repeated_pairs': pairs,
            'repeat_fraction': round(pairs / len(indices), 4) if indices else 0.0}


def geometry_summary(indices: list[int], stride: int) -> dict:
    """Summarize relative occupancy of changed words; do not output cell values."""
    if stride <= 0 or not indices or min(indices) < 0 or len(indices) != len(set(indices)):
        raise ValueError('Expected positive stride and unique nonempty indices')
    rows = Counter(i // stride for i in indices)
    columns = [i % stride for i in indices]
    return {
        'row_min': min(rows), 'row_max': max(rows),
        'column_min': min(columns), 'column_max': max(columns),
        'row_occupancies': [rows.get(r, 0) for r in range(min(rows), max(rows) + 1)],
        'bounding_rows': max(rows) - min(rows) + 1,
        'bounding_columns': max(columns) - min(columns) + 1,
    }


def analyze_pair(first: bytes, second: bytes) -> dict:
    """Cross-check uniqueness, paired values and footprint, never serialize raw IDs."""
    left, right = decode_record_table(first), decode_record_table(second)
    if len(left) != len(right):
        raise ValueError('Comparison requires equal active record counts')
    # Candidate word 1, at byte offset 2 of each 12-byte record.
    changed_records = difference_pairs(first, second, START + 2, 12, len(left))
    changed_tail = difference_pairs(first, second, TAIL_START, 2,
                                    (len(first) - TAIL_START) // 2)
    record_pairs = Counter(pair for _, pair in changed_records)
    tail_pairs = Counter(pair for _, pair in changed_tail)
    changed_indices = [i for i, _ in changed_tail]
    lag = candidate_stride(changed_indices)
    return {
        'active_records_each': len(left),
        'record_field_1_differences': len(changed_records),
        'tail_differences': len(changed_tail),
        'record_pair_values_unique': len(record_pairs) == len(changed_records),
        'tail_pair_values_unique': len(tail_pairs) == len(changed_tail),
        'pair_multisets_equal': record_pairs == tail_pairs,
        'one_to_one_pair_match': (bool(changed_records) and record_pairs == tail_pairs
                                  and len(record_pairs) == len(changed_records)),
        'stride_scan': lag,
        'candidate_footprint': geometry_summary(changed_indices, lag['candidate_lag'])
        if changed_indices else None,
        'interpretation': 'Candidate spatial ordering only; not an authenticated battle grid.'
    }


def analyze_image(image: Path, first_name: str = 'M_MAP13.MAP',
                  second_name: str = 'M_MAP14.MAP') -> dict:
    iso = SaturnISO(image)
    fs = iso.inspect(include_files=True)
    entries = {x['name']: x for x in fs['file_entries']}
    if first_name not in entries or second_name not in entries:
        raise ValueError('Comparison MAP files not present')
    with image.open('rb') as stream:
        first = read_file_payload(iso, stream, entries[first_name])
        second = read_file_payload(iso, stream, entries[second_name])
    return {
        'product_code': fs['boot_product_code'],
        'source_volume': fs['volume_id'],
        'first': first_name,
        'second': second_name,
        'results': analyze_pair(first, second),
        'warning': 'English v1.1 translation-patched disc. No original Japanese equivalence proven.'
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('track1', type=Path, help='Private Saturn RAW MODE1/2352 Track 1')
    p.add_argument('--left', default='M_MAP13.MAP')
    p.add_argument('--right', default='M_MAP14.MAP')
    p.add_argument('--output', type=Path, help='Numeric-only JSON output')
    args = p.parse_args()
    result = json.dumps(analyze_image(args.track1, args.left, args.right), indent=2) + '\n'
    if args.output:
        args.output.write_text(result, encoding='utf-8')
    else:
        print(result, end='')


if __name__ == '__main__':
    main()
