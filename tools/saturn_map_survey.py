#!/usr/bin/env python3
"""Produce metadata-only statistics of private Sega Saturn .MAP files.

No original game file bodies, tiles, graphics, or audio appear in reports.
Requires a locally owned Saturn RAW MODE1/2352 Track 1 image.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import BinaryIO

from tools.saturn_iso import SaturnISO

DATA_SIZE = 2048
MAX_MAP_BYTES = 8 * 1024 * 1024
CHUNK_BYTES = 16 * 1024


def read_file_payload(iso: SaturnISO, stream: BinaryIO, entry: dict) -> bytes:
    """Read one bounded file into private memory only."""
    start, size = entry['lba'], entry['bytes']
    if not isinstance(start, int) or not isinstance(size, int) or not 0 <= size <= MAX_MAP_BYTES:
        raise ValueError('Invalid MAP extent or size')
    sectors = (size + DATA_SIZE - 1) // DATA_SIZE
    if start < 0 or start + sectors > iso.sectors:
        raise ValueError('MAP extent outside image')
    return b''.join(iso.sector(stream, start + j) for j in range(sectors))[:size]


def file_family(name: str) -> str:
    for family in ('M_MAP', 'M_KEY', 'M_IVE'):
        if name.startswith(family):
            return family
    return 'OTHER'


def profile(name: str, data: bytes) -> dict:
    """Return numeric metrics and checksums, never input bytes."""
    if len(data) < 10:
        raise ValueError('MAP sample too small to profile')
    words = [int.from_bytes(data[i:i + 2], 'big') for i in range(0, 10, 2)]
    return {
        'name': name, 'family': file_family(name), 'length_bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
        'first_five_be16': words,
        'zero_byte_percent': round(data.count(0) * 100 / len(data), 2),
        'nonzero_per_16k': [sum(bool(v) for v in data[i:i + CHUNK_BYTES])
                            for i in range(0, len(data), CHUNK_BYTES)],
    }


def survey(iso: SaturnISO) -> dict:
    filesystem = iso.inspect(include_files=True)
    entries = [entry for entry in filesystem['file_entries']
               if entry['name'].upper().endswith('.MAP')]
    profiles = []
    private_bytes = {}  # Memory-only; never placed in returned JSON.
    with iso.path.open('rb') as stream:
        for entry in entries:
            body = read_file_payload(iso, stream, entry)
            profiles.append(profile(entry['name'], body))
            private_bytes[entry['name']] = body
    profiles.sort(key=lambda item: item['name'])
    identical, headers = defaultdict(list), defaultdict(list)
    for p in profiles:
        identical[p['sha256']].append(p['name'])
        headers[tuple(p['first_five_be16'][:4])].append(p['name'])
    comparisons = []
    for names in headers.values():
        if len(names) < 2:
            continue
        for index, left in enumerate(names):
            for right in names[index + 1:]:
                a, b = private_bytes[left], private_bytes[right]
                if len(a) != len(b):
                    continue
                offsets = [idx for idx, (x, y) in enumerate(zip(a, b)) if x != y]
                comparisons.append({
                    'left': left, 'right': right,
                    'different_bytes': len(offsets),
                    'first_difference_offset': offsets[0] if offsets else None,
                    'last_difference_offset': offsets[-1] if offsets else None,
                })
    summary = {
        'source_product_code': filesystem['boot_product_code'],
        'source_volume_id': filesystem['volume_id'],
        'map_count': len(profiles),
        'family_counts': dict(sorted(Counter(p['family'] for p in profiles).items())),
        'unique_map_lengths': sorted(set(p['length_bytes'] for p in profiles)),
        'header_word_3_eq_word_4': sum(p['first_five_be16'][2] == p['first_five_be16'][3]
                                      for p in profiles),
        'header_word_5_cdcd': sum(p['first_five_be16'][4] == 0xCDCD for p in profiles),
        'exact_duplicate_files': [names for names in identical.values() if len(names) > 1],
        'matching_first_four_word_groups': [names for names in headers.values()
                                           if len(names) > 1],
        'same_header_comparisons': comparisons,
        'min_zero_percent': min((p['zero_byte_percent'] for p in profiles), default=None),
        'max_zero_percent': max((p['zero_byte_percent'] for p in profiles), default=None),
    }
    return {
        'format': 'Sega Saturn .MAP metadata statistics (no original assets)',
        'summary': summary, 'maps': profiles,
        'warning': 'Field meanings unverified. English v1.1 is a modified release.',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('track1', type=Path, help='Local privately owned RAW MODE1 track')
    parser.add_argument('--output', type=Path, help='Write metadata-only JSON report')
    args = parser.parse_args()
    result = json.dumps(survey(SaturnISO(args.track1)), ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(result, encoding='utf-8')
    else:
        print(result, end='')


if __name__ == '__main__':
    main()
