#!/usr/bin/env python3
"""Stage 08: numerical survey of nonzero-word periodicity in Saturn MAP tails.

Reads a privately owned Saturn RAW MODE1/2352 disc. Returns frequencies and
candidate lags, never original game data or binary records. Periodicity is NOT
proof of a game-grid width, tile arrangement, or gameplay field semantics.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from tools.saturn_iso import SaturnISO
from tools.saturn_map_records import MAP_BYTES, TAIL_START
from tools.saturn_map_survey import file_family, read_file_payload

MIN_LAG = 16
MAX_LAG = 96
REFERENCE_LAG = 64


def nonzero_tail_words(data: bytes, start: int = TAIL_START) -> set[int]:
    """In-memory indexes of nonzero BE16 words; indexes are never exported."""
    if len(data) != MAP_BYTES or start < 0 or start >= len(data) or start % 2 or (len(data) - start) % 2:
        raise ValueError('Unsupported MAP size or tail alignment')
    tail = memoryview(data)[start:]
    return {index for index in range(len(tail) // 2)
            if tail[index * 2] != 0 or tail[index * 2 + 1] != 0}


def pitch_scores(indices: set[int], minimum: int = MIN_LAG,
                 maximum: int = MAX_LAG, reference: int = REFERENCE_LAG) -> dict:
    """Score pair recurrence at candidate lags with deterministic tie-breaking.

    The single best lag is the smallest among ties. Top-4 means membership in
    the first four sorted (lag, score) entries, not a statistical confidence.
    """
    if not indices or len(indices) != len(set(indices)) or any(i < 0 for i in indices):
        raise ValueError('Expected nonempty, nonnegative unique indices')
    if minimum < 1 or maximum < minimum or not minimum <= reference <= maximum:
        raise ValueError('Invalid lag bounds/reference')
    pairs = [(lag, sum((index + lag) in indices for index in indices))
             for lag in range(minimum, maximum + 1)]
    ranked = sorted(pairs, key=lambda item: (-item[1], item[0]))
    ref_score = next(score for lag, score in pairs if lag == reference)
    ref_rank = next(i + 1 for i, (lag, _) in enumerate(ranked) if lag == reference)
    return {
        'occupied_words': len(indices),
        'top_lag': ranked[0][0],
        'top_lag_pairs': ranked[0][1],
        'reference_lag': reference,
        'reference_pairs': ref_score,
        'reference_rank': ref_rank,
        'reference_is_first': ref_rank == 1,
        'reference_in_top_four': ref_rank <= 4,
        'top_four': [{'lag': lag, 'pairs': score} for lag, score in ranked[:4]],
    }


def summarize(profiles: list[dict]) -> dict:
    if not profiles:
        raise ValueError('At least one map is required')
    family_groups: dict[str, list[dict]] = {}
    for profile in profiles:
        family_groups.setdefault(profile['family'], []).append(profile)
    return {
        'map_count': len(profiles),
        'reference_first_count': sum(x['reference_is_first'] for x in profiles),
        'reference_top_four_count': sum(x['reference_in_top_four'] for x in profiles),
        'family_counts': {name: {
            'map_count': len(group),
            'reference_first_count': sum(x['reference_is_first'] for x in group),
            'reference_top_four_count': sum(x['reference_in_top_four'] for x in group),
            'not_in_top_four': [x['name'] for x in group if not x['reference_in_top_four']],
        } for name, group in sorted(family_groups.items())},
    }


def analyze_disc(iso: SaturnISO) -> dict:
    filesystem = iso.inspect(include_files=True)
    entries = sorted((entry for entry in filesystem['file_entries']
                      if entry['name'].upper().endswith('.MAP')),
                     key=lambda entry: entry['name'])
    if not entries:
        raise ValueError('Disc does not contain .MAP files')
    profiles = []
    with iso.path.open('rb') as stream:
        for entry in entries:
            body = read_file_payload(iso, stream, entry)
            indices = nonzero_tail_words(body)
            if not indices:
                raise ValueError('MAP has an empty candidate tail')
            family = file_family(entry['name'])
            if entry['name'] == 'M_SHOW.MAP':
                family = 'M_SHOW'
            profiles.append({'name': entry['name'], 'family': family,
                             **pitch_scores(indices)})
    return {
        'source_product_code': filesystem['boot_product_code'],
        'source_volume_id': filesystem['volume_id'],
        'candidate_tail_start': TAIL_START,
        'candidate_end_exclusive': MAP_BYTES,
        'candidate_lag_range_inclusive': [MIN_LAG, MAX_LAG],
        'reference_lag': REFERENCE_LAG,
        'summary': summarize(profiles),
        'maps': profiles,
        'limits': ('Nonzero BE16-word positional autocorrelation only; '
                   'does not prove Saturn tile/grid semantics. '
                   'Input is the English v1.1 translated release.'),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('track1', type=Path, help='Private Saturn RAW MODE1/2352 Track 1')
    parser.add_argument('--output', type=Path, help='Write metadata-only JSON report')
    args = parser.parse_args()
    payload = json.dumps(analyze_disc(SaturnISO(args.track1)), indent=2,
                         ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(payload, encoding='utf-8')
    else:
        print(payload, end='')


if __name__ == '__main__':
    main()
