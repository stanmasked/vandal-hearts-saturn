"""Synthetic-only tests. No original copyrighted data used."""
import unittest

from tools.saturn_map_records import (
    START, END, TAIL_START, MAP_BYTES, RECORD_BYTES,
    decode_record_table, profile, altered_word_pairs, compare_linked_fields,
)


def make_map(records):
    data = bytearray(MAP_BYTES)
    for i, record in enumerate(records):
        start = START + i * RECORD_BYTES
        for j, value in enumerate(record):
            data[start + j * 2:start + j * 2 + 2] = value.to_bytes(2, 'big')
    return data


class MapRecordTests(unittest.TestCase):
    def test_exact_table_capacity(self):
        self.assertEqual((END - START) // RECORD_BYTES, 1707)
        self.assertEqual((END - START) % RECORD_BYTES, 0)

    def test_active_prefix_and_padding(self):
        a = make_map([(1, 4, 6, 0, 10, 2), (1, 7, 6, 0, 10, 2)])
        self.assertEqual(decode_record_table(a), [(1, 4, 6, 0, 10, 2),
                                                   (1, 7, 6, 0, 10, 2)])
        p = profile(a)
        self.assertEqual(p['active_records'], 2)
        self.assertEqual(p['padding_records'], 1705)
        self.assertEqual(p['varying_field_indices'], [1])
        self.assertEqual(p['constant_field_indices'], [0, 2, 3, 4, 5])

    def test_full_table_allowed(self):
        a = make_map([(1, 2, 3, 0, 4, 5)] * 1707)
        self.assertEqual(profile(a)['active_records'], 1707)

    def test_gap_then_nonzero_rejected(self):
        a = make_map([(1, 2, 3, 0, 4, 5), (0, 0, 0, 0, 0, 0),
                      (1, 2, 3, 0, 4, 5)])
        with self.assertRaises(ValueError):
            decode_record_table(a)

    def test_wrong_map_size_rejected(self):
        with self.assertRaises(ValueError):
            decode_record_table(b'\0' * 16)

    def test_mirrored_change_pairs(self):
        a = make_map([(1, 12, 3, 0, 4, 5), (1, 22, 3, 0, 4, 5)])
        b = make_map([(1, 13, 3, 0, 8, 5), (1, 23, 3, 0, 4, 5)])
        a[TAIL_START:TAIL_START + 4] = b'\x00\x16\x00\x0c'
        b[TAIL_START:TAIL_START + 4] = b'\x00\x17\x00\x0d'
        result = compare_linked_fields(a, b)
        self.assertEqual(result['changed_record_fields'], [0, 2, 0, 0, 1, 0])
        self.assertEqual(result['different_bytes'], 5)
        self.assertEqual(result['different_even_offsets'], 0)
        self.assertEqual(result['mirrored_field_1_tail_changes'], 2)
        self.assertTrue(result['field_1_tail_multiset_equal'])
        self.assertNotIn('0x16', str(result))

    def test_mismatched_reference_changes(self):
        a = make_map([(1, 12, 3, 0, 4, 5)])
        b = make_map([(1, 13, 3, 0, 4, 5)])
        a[TAIL_START:TAIL_START + 2] = b'\x00\x15'
        b[TAIL_START:TAIL_START + 2] = b'\x00\x17'
        result = compare_linked_fields(a, b)
        self.assertEqual(result['mirrored_field_1_tail_changes'], 0)
        self.assertFalse(result['field_1_tail_multiset_equal'])

    def test_mismatched_active_counts(self):
        a = make_map([(1, 12, 3, 0, 4, 5)])
        b = make_map([(1, 12, 3, 0, 4, 5)] * 2)
        with self.assertRaises(ValueError):
            compare_linked_fields(a, b)

    def test_private_pairs_not_serialized(self):
        a = bytes.fromhex('00110021')
        b = bytes.fromhex('00220031')
        changes = altered_word_pairs(a, b, 0, 4, 2, 0)
        self.assertEqual(sum(changes.values()), 2)
        self.assertEqual(changes[(0x11, 0x22)], 1)


if __name__ == '__main__':
    unittest.main()
