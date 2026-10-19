#!/usr/bin/env python3
"""Metadata-only survey of the suspected 12-byte table in Saturn .MAP files.

All research hypotheses are unverified. Read user-owned game bytes locally,
report numeric counts only. Do not print/extract original records or assets.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from tools.saturn_iso import SaturnISO
from tools.saturn_map_survey import read_file_payload

START = 0x1E800
END = 0x23804  # exclusive: (END-START)//12 = 1707
TAIL_START = 0x24400
RECORD_BYTES = 12
WORDS = 6
MAP_BYTES = 170624


def decode_record_table(data: bytes) -> list[tuple[int, ...]]:
    """Parse candidate 6 x BE16 entries up to the first all-zero record.

    Strictly reject partial records and a nonzero record after zero padding.
    This is structural parsing ONLY; no gameplay meaning is attached.
    """
    if len(data) != MAP_BYTES or (END - START) % RECORD_BYTES:
        raise ValueError('Unsupported MAP length or record layout')
    active = []
    in_padding = False
    for off in range(START, END, RECORD_BYTES):
        words = tuple(int.from_bytes(data[off + i:off + i + 2], 'big')
                      for i in range(0, RECORD_BYTES, 2))
        if words == (0,) * WORDS:
            in_padding = True
        elif in_padding:
            raise ValueError('Nonzero candidate record after zero padding')
        else:
            active.append(words)
    return active


def profile(data: bytes) -> dict:
    active = decode_record_table(data)
    distinct_per_word = [len({record[pos] for record in active}) for pos in range(WORDS)]
    return {
        'active_records': len(active),
        'capacity_records': (END - START) // RECORD_BYTES,
        'padding_records': (END - START) // RECORD_BYTES - len(active),
        'constant_field_indices': [i for i, n in enumerate(distinct_per_word) if n == 1],
        'varying_field_indices': [i for i, n in enumerate(distinct_per_word) if n > 1],
        'distinct_value_counts_by_field': distinct_per_word,
    }


def altered_word_pairs(a: bytes, b: bytes, start: int, end: int, stride: int,
                       field_offset: int) -> Counter:
    """Return private in-memory 16-bit change counts; caller must not serialize!"""
    if len(a) != len(b) or start < 0 or end > len(a) or stride <= 0 or field_offset < 0 \
            or field_offset + 2 > stride:
        raise ValueError('Invalid comparative layout')
    pairs = Counter()
    for off in range(start + field_offset, end - 1, stride):
        before = int.from_bytes(a[off:off + 2], 'big')
        after = int.from_bytes(b[off:off + 2], 'big')
        if before != after:
            pairs[(before, after)] += 1
    return pairs


def compare_linked_fields(a: bytes, b: bytes) -> dict:
    """Compare record fields with a later BE16 table using multiset equality.

    Output only the number of changes and whether each change was mirrored.
    The pair values are deliberately never exported.
    """
    left = decode_record_table(a)
    right = decode_record_table(b)
    if len(left) != len(right):
        raise ValueError('Record counts differ; comparison requires aligned tables')
    count = len(left)
    changes_in_fields = [sum(l[index] != r[index] for l, r in zip(left, right))
                         for index in range(WORDS)]
    record_field_1 = altered_word_pairs(a, b, START, START + count * RECORD_BYTES,
                                         RECORD_BYTES, 2)
    # Tail is a separate *candidate* BE16-aligned table; its role is unknown.
    tail = altered_word_pairs(a, b, TAIL_START, len(a), 2, 0)
    matching = sum((record_field_1 & tail).values())
    # Reject unaligned byte differences instead of concealing them.
    changed_bytes = sum(x != y for x, y in zip(a, b))
    changed_even = sum(a[i] != b[i] for i in range(0, len(a), 2))
    changed_odd = changed_bytes - changed_even
    return {
        'different_bytes': changed_bytes,
        'different_even_offsets': changed_even,
        'different_odd_offsets': changed_odd,
        'record_count_both': count,
        'changed_record_fields': changes_in_fields,
        'changed_tail_words': sum(tail.values()),
        'mirrored_field_1_tail_changes': matching,
        'field_1_tail_multiset_equal': record_field_1 == tail,
        'note': ('The tail values may be related references; multiset equality '
                 'does not establish graphics or gameplay semantics.'),
    }


def analyze(iso: SaturnISO, left: str = 'M_MAP13.MAP',
            right: str = 'M_MAP14.MAP') -> dict:
    fs = iso.inspect(include_files=True)
    entries = [entry for entry in fs['file_entries']
               if entry['name'].upper().endswith('.MAP')]
    if not entries:
        raise ValueError('No MAP files present')
    data = {}
    with iso.path.open('rb') as stream:
        for entry in entries:
            data[entry['name']] = read_file_payload(iso, stream, entry)
    if left not in data or right not in data:
        raise ValueError('Named comparison files not found')
    profiles = {name: profile(blob) for name, blob in sorted(data.items())}
    # This is not game-data export: only aggregate distinct constant word pairs.
    kinds = Counter()
    for blob in data.values():
        records = decode_record_table(blob)
        if not records:
            raise ValueError('Empty candidate record table')
        kinds[(records[0][0], records[0][2])] += 1
    return {
        'source_product_code': fs['boot_product_code'],
        'source_volume_id': fs['volume_id'],
        'files_analyzed': len(profiles),
        'record_start': START,
        'record_end_exclusive': END,
        'record_bytes': RECORD_BYTES,
        'candidate_record_kinds': [
            {'first_and_third_be16': [a, b], 'maps': n}
            for (a, b), n in sorted(kinds.items())],
        'sum_active_records': sum(x['active_records'] for x in profiles.values()),
        'active_record_min': min(x['active_records'] for x in profiles.values()),
        'active_record_max': max(x['active_records'] for x in profiles.values()),
        'map_profiles': profiles,
        'comparison': {'left': left, 'right': right,
                       **compare_linked_fields(data[left], data[right])},
        'warning': 'Field meanings unverified. Source is the English v1.1 patched Saturn release.',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('track1', type=Path, help='Private RAW MODE1/2352 Track 1')
    parser.add_argument('--left', default='M_MAP13.MAP')
    parser.add_argument('--right', default='M_MAP14.MAP')
    parser.add_argument('--output', type=Path, help='Numeric-only JSON output file')
    args = parser.parse_args()
    result = json.dumps(analyze(SaturnISO(args.track1), args.left, args.right),
                        indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(result, encoding='utf-8')
    else:
        print(result, end='')


if __name__ == '__main__':
    main()
