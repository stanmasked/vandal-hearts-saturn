"""Purely synthetic tests for structural correlations; no original disc data."""
import unittest

from tools.saturn_map_patch import (
    candidate_stride, geometry_summary, difference_pairs, analyze_pair,
)
from tools.saturn_map_records import START, TAIL_START, MAP_BYTES


def fixture(mirrored=True):
    first, second = bytearray(MAP_BYTES), bytearray(MAP_BYTES)
    mask = [(row, col) for row, min_col, max_col in
            [(4, 6, 10), (5, 5, 11), (6, 4, 12), (7, 4, 12), (8, 4, 12),
             (9, 4, 12), (10, 4, 12), (11, 5, 11), (12, 6, 10)]
            for col in range(min_col, max_col + 1)]
    # Synthetic 12-byte records and a tail word array, with a deliberately
    # different order and unique before/after pairs in each section.
    for i, (row, col) in enumerate(mask):
        rec = START + i * 12
        for data in (first, second):
            for at, val in [(0, 326), (4, 192), (8, 63220), (10, 2)]:
                data[rec + at:rec + at + 2] = val.to_bytes(2, 'big')
        before, after = i + 1, i + 101
        first[rec + 2:rec + 4] = before.to_bytes(2, 'big')
        second[rec + 2:rec + 4] = after.to_bytes(2, 'big')
        # Reverse the correspondence so ordering alone cannot produce match.
        reverse_idx = len(mask) - 1 - i
        tail_idx = mask[reverse_idx][0] * 64 + mask[reverse_idx][1]
        at = TAIL_START + tail_idx * 2
        first[at:at + 2] = before.to_bytes(2, 'big')
        second[at:at + 2] = (after if mirrored else after + 1).to_bytes(2, 'big')
    return bytes(first), bytes(second)


class Stage07Tests(unittest.TestCase):
    def test_candidate_repeat_lag(self):
        indexes = [r * 64 + c for r in range(4, 13) for c in range(4, 13)]
        self.assertEqual(candidate_stride(indexes)['candidate_lag'], 64)
        self.assertEqual(candidate_stride(indexes)['repeated_pairs'], 72)

    def test_footprint(self):
        indexes = [r * 64 + c for r, cols in enumerate([[1, 2], [1, 2, 3], [2, 3]])
                   for c in cols]
        footprint = geometry_summary(indexes, 64)
        self.assertEqual(footprint['row_occupancies'], [2, 3, 2])
        self.assertEqual(footprint['bounding_columns'], 3)

    def test_realistic_synthetic_patch(self):
        a, b = fixture()
        result = analyze_pair(a, b)
        self.assertEqual(result['active_records_each'], 69)
        self.assertEqual(result['record_field_1_differences'], 69)
        self.assertEqual(result['tail_differences'], 69)
        self.assertTrue(result['one_to_one_pair_match'])
        self.assertEqual(result['stride_scan']['candidate_lag'], 64)
        self.assertEqual(result['stride_scan']['repeated_pairs'], 60)
        self.assertEqual(result['candidate_footprint']['row_occupancies'],
                         [5, 7, 9, 9, 9, 9, 9, 7, 5])

    def test_pair_corruption(self):
        a, b = fixture(mirrored=False)
        result = analyze_pair(a, b)
        self.assertFalse(result['one_to_one_pair_match'])
        self.assertFalse(result['pair_multisets_equal'])

    def test_empty_inputs_and_invalid(self):
        self.assertEqual(candidate_stride([])['repeated_pairs'], 0)
        for fn in (lambda: candidate_stride([1, 1]),
                   lambda: candidate_stride([1], 0, 10),
                   lambda: candidate_stride([1], 10, 9),
                   lambda: geometry_summary([], 64),
                   lambda: geometry_summary([0, 1], 0),
                   lambda: difference_pairs(b'ab', b'ab', 1, 2, 1)):
            with self.assertRaises(ValueError):
                fn()

    def test_difference_pairs(self):
        self.assertEqual(difference_pairs(b'\x00\x05\x00\x06',
                                          b'\x00\x05\x00\x09', 0, 2, 2),
                         [(1, (6, 9))])


if __name__ == '__main__':
    unittest.main()
