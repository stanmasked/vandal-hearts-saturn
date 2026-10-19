#!/usr/bin/env python3
"""Profile structural similarity between privately held Saturn MAP files.

Read originals only from an owned local RAW MODE1/2352 Saturn disc.
Export numeric summaries only; no game bytes, tiles, art or audio.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.saturn_iso import SaturnISO
from tools.saturn_map_survey import read_file_payload

WINDOW = 4096


def _validate(samples: list[bytes]) -> int:
    if not samples:
        raise ValueError('Expected at least one MAP sample')
    size = len(samples[0])
    if size < 1 or any(len(s) != size for s in samples):
        raise ValueError('MAP samples must have the same nonzero length')
    return size


def common_zero_ranges(samples: list[bytes], min_size: int = 512) -> list[dict]:
    """Identify offsets zero in every sample. End offsets are exclusive."""
    size = _validate(samples)
    if min_size < 1:
        raise ValueError('min_size must be positive')
    mask = bytearray(size)
    for sample in samples:
        for index, value in enumerate(sample):
            if value:
                mask[index] = 1
    intervals = []
    start = None
    for index, nonzero in enumerate(mask):
        if nonzero:
            if start is not None and index - start >= min_size:
                intervals.append({'start': start, 'end_exclusive': index,
                                  'length_bytes': index - start})
            start = None
        elif start is None:
            start = index
    if start is not None and size - start >= min_size:
        intervals.append({'start': start, 'end_exclusive': size,
                          'length_bytes': size - start})
    return intervals


def occupancy_windows(samples: list[bytes], window_bytes: int = WINDOW) -> list[dict]:
    """Count nonzero samples per window, without leaking bytes."""
    size = _validate(samples)
    if window_bytes < 1:
        raise ValueError('window_bytes must be positive')
    return [{'start': start, 'end_exclusive': min(size, start + window_bytes),
             'maps_with_nonzero_bytes': sum(any(sample[start:start + window_bytes]) for sample in samples),
             'nonzero_byte_total': sum(sum(byte != 0 for byte in sample[start:start + window_bytes])
                                       for sample in samples)}
            for start in range(0, size, window_bytes)]


def compare_pair(first: bytes, second: bytes, window_bytes: int = WINDOW) -> dict:
    """Diff offsets and byte-parity statistics; never return source bytes."""
    _validate([first, second])
    if window_bytes < 1:
        raise ValueError('window_bytes must be positive')
    changed = [i for i, (a, b) in enumerate(zip(first, second)) if a != b]
    by_window = {}
    for index in changed:
        start = index // window_bytes * window_bytes
        by_window[start] = by_window.get(start, 0) + 1
    return {
        'different_bytes': len(changed),
        'different_16bit_words': len(set(index // 2 for index in changed)),
        'different_even_offsets': sum(index % 2 == 0 for index in changed),
        'different_odd_offsets': sum(index % 2 == 1 for index in changed),
        'zero_nonzero_mask_identical': all(bool(a) == bool(b) for a, b in zip(first, second)),
        'first_difference_offset': changed[0] if changed else None,
        'last_difference_offset': changed[-1] if changed else None,
        'changed_windows': [{'start': start, 'different_bytes': by_window[start]}
                            for start in sorted(by_window)],
    }


def analyze(iso: SaturnISO, left: str = 'M_MAP13.MAP',
            right: str = 'M_MAP14.MAP', window_bytes: int = WINDOW,
            min_zero_size: int = 512) -> dict:
    fs = iso.inspect(include_files=True)
    entries = [entry for entry in fs['file_entries'] if entry['name'].upper().endswith('.MAP')]
    if not entries:
        raise ValueError('No MAP files on disc')
    samples = {}
    with iso.path.open('rb') as stream:
        for entry in entries:
            samples[entry['name']] = read_file_payload(iso, stream, entry)
    lengths = sorted({len(sample) for sample in samples.values()})
    if len(lengths) != 1:
        raise ValueError('Cannot compare files of differing sizes')
    if left not in samples or right not in samples:
        raise ValueError('Specified comparison MAP files are missing')
    batch = list(samples.values())
    return {
        'source_volume_id': fs['volume_id'],
        'source_product_code': fs['boot_product_code'],
        'map_files': len(samples),
        'map_file_bytes': lengths[0],
        'window_bytes': window_bytes,
        'common_zero_ranges': common_zero_ranges(batch, min_zero_size),
        'occupancy_windows': occupancy_windows(batch, window_bytes),
        'pair': {'left': left, 'right': right, **compare_pair(samples[left], samples[right], window_bytes)},
        'limitations': ('All offsets are absolute file offsets. Region boundaries and MAP semantics are'
                        ' unknown; English v1.1 may differ from original Japanese Saturn release.'),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('track1', type=Path, help='Locally held Sega Saturn RAW MODE1 track')
    parser.add_argument('--left', default='M_MAP13.MAP')
    parser.add_argument('--right', default='M_MAP14.MAP')
    parser.add_argument('--output', type=Path, help='Write JSON with numeric stats only')
    args = parser.parse_args()
    report = json.dumps(analyze(SaturnISO(args.track1), args.left, args.right), indent=2,
                        ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    else:
        print(report, end='')


if __name__ == '__main__':
    main()
