#!/usr/bin/env python3
"""Read-only, metadata-only test of MAP record-word ↔ candidate layer A association.

All original Saturn bytes stay in private process memory; the JSON contains
only counts and ratios. Matching value multisets does NOT establish a grid
coordinate mapping, terrain, graphics, or original gameplay semantics.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from tools.saturn_iso import SaturnISO
from tools.saturn_map_records import TAIL_START, decode_record_table
from tools.saturn_map_survey import file_family, read_file_payload

LAYER_A_WORDS = 28 * 64


def multiset_overlap(left: Counter, right: Counter) -> int:
    """Count equal values *with multiplicity*; never expose those values."""
    if any(v < 0 for v in left.values()) or any(v < 0 for v in right.values()):
        raise ValueError('Counter values must be nonnegative')
    return sum((left & right).values())


def counters_from_map(data: bytes) -> tuple[Counter, Counter]:
    """Private candidate layer A and record-word 1 multisets."""
    records = decode_record_table(data)
    if not records:
        raise ValueError('No active candidate records')
    end = TAIL_START + 2 * LAYER_A_WORDS
    layer = [int.from_bytes(data[i:i + 2], 'big')
             for i in range(TAIL_START, end, 2)]
    if len(layer) != LAYER_A_WORDS:
        raise ValueError('Truncated candidate layer')
    return Counter(v for v in layer if v != 0), Counter(row[1] for row in records)


def analyze_counters(samples: dict[str, tuple[Counter, Counter]]) -> dict:
    """Same-map matches vs leave-one-map-out, same-family controls."""
    if not samples:
        raise ValueError('No maps supplied')
    groups = defaultdict(list)
    for name, (layer, records) in samples.items():
        if not name.upper().endswith('.MAP'):
            raise ValueError('Unexpected map filename')
        if not layer or not records:
            raise ValueError('Each sample requires a nonempty layer and record table')
        family = 'M_SHOW' if name == 'M_SHOW.MAP' else file_family(name)
        groups[family].append(name)
    profiles = {}
    for family, names in sorted(groups.items()):
        for name in sorted(names):
            layer, records = samples[name]
            total = sum(layer.values())
            own = multiset_overlap(layer, records)
            controls = [multiset_overlap(layer, samples[other][1])
                        for other in names if other != name]
            strongest = max(controls) if controls else None
            mean_control_fraction = sum(controls) / (total * len(controls)) if controls else None
            profiles[name] = {
                'family': family,
                'layer_nonzero_words': total,
                'record_words': sum(records.values()),
                'same_map_matches': own,
                'same_map_fraction': round(own / total, 6),
                'layer_multiset_subsumed_by_records': own == total,
                'other_maps_in_family': len(controls),
                'foreign_max_matches': strongest,
                'foreign_mean_fraction': (round(mean_control_fraction, 6)
                                          if mean_control_fraction is not None else None),
                'strict_self_best': (own > strongest if strongest is not None else None),
                'ties_best_foreign': (own == strongest if strongest is not None else None),
                'foreign_exceeds_self': (strongest > own if strongest is not None else None),
            }
    families = {}
    for family, names in sorted(groups.items()):
        ps = [profiles[n] for n in names]
        with_controls = [p for p in ps if p['other_maps_in_family']]
        families[family] = {
            'map_count': len(ps),
            'layer_words_total': sum(p['layer_nonzero_words'] for p in ps),
            'self_matches_total': sum(p['same_map_matches'] for p in ps),
            'self_matches_weighted_fraction': round(
                sum(p['same_map_matches'] for p in ps) /
                sum(p['layer_nonzero_words'] for p in ps), 6),
            'self_fraction_mean': round(sum(p['same_map_fraction'] for p in ps) / len(ps), 6),
            'foreign_fraction_mean': (round(sum(p['foreign_mean_fraction'] for p in with_controls)
                                            / len(with_controls), 6)
                                      if with_controls else None),
            'strict_self_wins': sum(p['strict_self_best'] is True for p in ps),
            'tied_best_foreign': sum(p['ties_best_foreign'] is True for p in ps),
            'foreign_wins': sum(p['foreign_exceeds_self'] is True for p in ps),
        }
    return {
        'map_count': len(profiles),
        'layer_nonzero_total': sum(p['layer_nonzero_words'] for p in profiles.values()),
        'same_map_matches_total': sum(p['same_map_matches'] for p in profiles.values()),
        'multiset_subset_map_count': sum(p['layer_multiset_subsumed_by_records']
                                        for p in profiles.values()),
        'controlled_map_count': sum(bool(p['other_maps_in_family']) for p in profiles.values()),
        'strict_self_wins': sum(p['strict_self_best'] is True for p in profiles.values()),
        'ties_best_foreign': sum(p['ties_best_foreign'] is True for p in profiles.values()),
        'foreign_wins': sum(p['foreign_exceeds_self'] is True for p in profiles.values()),
        'families': families,
        'maps': {n: profiles[n] for n in sorted(profiles)},
    }


def analyze_disc(iso: SaturnISO) -> dict:
    filesystem = iso.inspect(include_files=True)
    entries = [entry for entry in filesystem['file_entries']
               if entry['name'].upper().endswith('.MAP')]
    samples = {}
    with iso.path.open('rb') as stream:
        for entry in entries:
            samples[entry['name']] = counters_from_map(read_file_payload(iso, stream, entry))
    return {
        'product_code': filesystem['boot_product_code'],
        'source_volume': filesystem['volume_id'],
        'candidate_layer_a_words': LAYER_A_WORDS,
        'candidate_record_word_index': 1,
        'results': analyze_counters(samples),
        'limitations': ('Multiset overlap is not a positional correspondence. '
                        'The source is translation-patched English v1.1, not a '
                        'verified original Japanese Saturn disc.'),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('track1', type=Path, help='Local, owned Saturn Track 1 BIN')
    parser.add_argument('--output', type=Path, help='Numeric-only JSON output')
    args = parser.parse_args()
    report = json.dumps(analyze_disc(SaturnISO(args.track1)),
                        indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    else:
        print(report, end='')


if __name__ == '__main__':
    main()
