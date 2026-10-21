"""Tests are fully synthetic and do not touch any original Saturn media."""
import unittest

from tools.saturn_map_structure import common_zero_ranges, occupancy_windows, compare_pair


class MapStructureTests(unittest.TestCase):
    def test_common_zero_ranges(self):
        result = common_zero_ranges([b'\x01\x00\x00\x00\x00\x05\x00\x00',
                                     b'\x00\x00\x00\x00\x00\x02\x00\x00'], 2)
        self.assertEqual(result, [
            {'start': 1, 'end_exclusive': 5, 'length_bytes': 4},
            {'start': 6, 'end_exclusive': 8, 'length_bytes': 2}])

    def test_trailing_zero_run(self):
        self.assertEqual(common_zero_ranges([b'\x00' * 9], 9),
                         [{'start': 0, 'end_exclusive': 9, 'length_bytes': 9}])

    def test_zero_run_minimum(self):
        self.assertEqual(common_zero_ranges([b'\x00\x01\x00'], 2), [])

    def test_occupancy_partial_last_window(self):
        samples = [b'\x01\x00\x00\x00\x00\x02', b'\x00\x01\x00\x00\x00\x00']
        self.assertEqual(occupancy_windows(samples, 4), [
            {'start': 0, 'end_exclusive': 4, 'maps_with_nonzero_bytes': 2,
             'nonzero_byte_total': 2},
            {'start': 4, 'end_exclusive': 6, 'maps_with_nonzero_bytes': 1,
             'nonzero_byte_total': 1}])

    def test_pair_changed_odd_offsets(self):
        first = b'\x12\x34\x00\x01\x56\x78\x00\x03'
        second = b'\x12\x35\x00\x02\x56\x79\x00\x04'
        d = compare_pair(first, second, 4)
        self.assertEqual(d['different_bytes'], 4)
        self.assertEqual(d['different_16bit_words'], 4)
        self.assertEqual(d['different_even_offsets'], 0)
        self.assertEqual(d['different_odd_offsets'], 4)
        self.assertTrue(d['zero_nonzero_mask_identical'])
        self.assertEqual(d['changed_windows'], [
            {'start': 0, 'different_bytes': 2}, {'start': 4, 'different_bytes': 2}])
        self.assertNotIn('52', str(d))  # source byte values are never included

    def test_pair_changed_zero_mask_and_empty(self):
        self.assertFalse(compare_pair(b'\x00\x01', b'\x03\x01')['zero_nonzero_mask_identical'])
        d = compare_pair(b'\x02\x01', b'\x02\x01')
        self.assertIsNone(d['first_difference_offset'])
        self.assertEqual(d['different_bytes'], 0)
        self.assertEqual(d['changed_windows'], [])

    def test_invalid_input(self):
        for samples in ([], [b''], [b'a', b'zz']):
            with self.assertRaises(ValueError):
                common_zero_ranges(samples)
        for fn in (lambda: compare_pair(b'a', b'aa'),
                   lambda: occupancy_windows([b'x'], 0),
                   lambda: common_zero_ranges([b'x'], 0)):
            with self.assertRaises(ValueError):
                fn()


if __name__ == '__main__':
    unittest.main()
