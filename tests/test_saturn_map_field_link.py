"""Synthetic-only tests; no original Saturn bytes or assets."""
import unittest
from collections import Counter

from tools.saturn_map_field_link import (
    analyze_counters, counters_from_map, multiset_overlap,
)
from tools.saturn_map_records import MAP_BYTES, START, TAIL_START


def synthetic_map(record_values, layer_values):
    data = bytearray(MAP_BYTES)
    for row, value in enumerate(record_values):
        off = START + row * 12
        for word_i, word in enumerate((326, value, 192, 0, 63220, 2)):
            data[off + word_i * 2:off + word_i * 2 + 2] = word.to_bytes(2, 'big')
    for i, value in enumerate(layer_values):
        off = TAIL_START + i * 2
        data[off:off + 2] = value.to_bytes(2, 'big')
    return bytes(data)


class MapFieldLinkTests(unittest.TestCase):
    def test_multiset_overlap_counts_repetitions(self):
        self.assertEqual(multiset_overlap(Counter([1, 1, 1, 2]),
                                          Counter([1, 1, 3, 2])), 3)

    def test_overlapping_values_without_multiplicity(self):
        self.assertEqual(multiset_overlap(Counter([1, 1, 1]), Counter([1])), 1)

    def test_rejects_negative_counts(self):
        with self.assertRaises(ValueError):
            multiset_overlap(Counter({4: -1}), Counter({4: 3}))

    def test_extract_candidate_fields(self):
        layer, records = counters_from_map(synthetic_map([10, 20, 20], [20, 10, 0]))
        self.assertEqual(layer, Counter([10, 20]))
        self.assertEqual(records, Counter([10, 20, 20]))

    def test_empty_record_table_rejected(self):
        with self.assertRaises(ValueError):
            counters_from_map(bytes(MAP_BYTES))

    def test_own_map_beats_control(self):
        s = {
            'M_MAP01.MAP': (Counter([4, 4, 9]), Counter([4, 4, 9, 7])),
            'M_MAP02.MAP': (Counter([7, 7]), Counter([7, 7, 8])),
        }
        result = analyze_counters(s)
        self.assertEqual(result['strict_self_wins'], 2)
        self.assertEqual(result['foreign_wins'], 0)
        self.assertEqual(result['same_map_matches_total'], 5)
        self.assertEqual(result['families']['M_MAP']['map_count'], 2)
        self.assertEqual(result['maps']['M_MAP01.MAP']['foreign_max_matches'], 0)

    def test_tie_can_occur(self):
        s = {
            'M_MAP01.MAP': (Counter([1]), Counter([1])),
            'M_MAP02.MAP': (Counter([2]), Counter([1, 2])),
        }
        result = analyze_counters(s)
        self.assertEqual(result['ties_best_foreign'], 1)
        self.assertEqual(result['strict_self_wins'], 1)

    def test_unequal_cross_controls_and_foreign_win(self):
        s = {
            'M_KEY01.MAP': (Counter([2, 2]), Counter([2])),
            'M_KEY02.MAP': (Counter([3, 3]), Counter([2, 2, 3, 3])),
        }
        result = analyze_counters(s)
        self.assertEqual(result['foreign_wins'], 1)
        self.assertEqual(result['maps']['M_KEY01.MAP']['same_map_matches'], 1)

    def test_singleton_family_has_no_foreign_control(self):
        s = {'M_SHOW.MAP': (Counter([1]), Counter([1]))}
        result = analyze_counters(s)
        self.assertEqual(result['controlled_map_count'], 0)
        self.assertIsNone(result['families']['M_SHOW']['foreign_fraction_mean'])
        self.assertIsNone(result['maps']['M_SHOW.MAP']['strict_self_best'])

    def test_empty_and_malformed_inputs(self):
        with self.assertRaises(ValueError):
            analyze_counters({})
        with self.assertRaises(ValueError):
            analyze_counters({'bad.txt': (Counter([1]), Counter([1]))})
        with self.assertRaises(ValueError):
            analyze_counters({'M_MAP01.MAP': (Counter(), Counter([1]))})


if __name__ == '__main__':
    unittest.main()
