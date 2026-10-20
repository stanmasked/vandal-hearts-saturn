"""Stage 11 synthetic-only unit tests, independent of original Saturn media."""
import unittest
from tools.saturn_map_correspondence import (
    analyze_samples, candidate_data, multiset_match_table, unique_anchor_order,
)
from tools.saturn_map_records import START, TAIL_START, MAP_BYTES


def sample(records, a_words, b_words=()):
    data = bytearray(MAP_BYTES)
    for i, word1 in enumerate(records):
        for j, value in enumerate((326, word1, 192, 0, 450, 2)):
            at = START + i * 12 + j * 2
            data[at:at + 2] = value.to_bytes(2, "big")
    for row, values in ((0, a_words), (28, b_words)):
        for i, value in enumerate(values):
            at = TAIL_START + row * 64 * 2 + i * 2
            data[at:at + 2] = value.to_bytes(2, "big")
    return bytes(data)


class Stage11Tests(unittest.TestCase):
    def test_structural_regions(self):
        rec, regions = candidate_data(sample([1, 2, 2], [2, 1]))
        self.assertEqual(len(regions["A"]), 1792)
        self.assertEqual(len(regions["B"]), 1792)
        self.assertEqual(len(regions["E"]), 4800)
        self.assertEqual(len(rec), 3)

    def test_field_specificity(self):
        rec, regions = candidate_data(sample([100, 101], [101, 100], [900, 901]))
        table, counts = multiset_match_table(rec, regions)
        self.assertEqual(table["A"], [0, 2, 0, 0, 0, 0])
        self.assertEqual(table["B"], [0, 0, 0, 0, 0, 0])
        self.assertEqual(counts["A"], 2)

    def test_multiplicity(self):
        rec, regions = candidate_data(sample([10, 10], [10, 10, 10]))
        table, counts = multiset_match_table(rec, regions)
        self.assertEqual(table["A"][1], 2)
        self.assertEqual(counts["A"], 3)

    def test_anchor_order_increasing_and_decreasing(self):
        rec, regions = candidate_data(sample([10, 20, 30], [20, 10, 30]))
        a = unique_anchor_order(rec, regions["A"])
        self.assertEqual(a["unambiguous_anchors"], 3)
        self.assertEqual(a["adjacent_ascending"], 1)
        self.assertEqual(a["adjacent_descending"], 1)

    def test_duplicates_are_not_assigned(self):
        rec, regions = candidate_data(sample([10, 10, 30], [10, 30]))
        self.assertEqual(unique_anchor_order(rec, regions["A"])["unambiguous_anchors"], 1)
        rec, regions = candidate_data(sample([10, 30], [10, 10, 30]))
        self.assertEqual(unique_anchor_order(rec, regions["A"])["unambiguous_anchors"], 1)

    def test_no_anchors_from_unmatched_values(self):
        rec, regions = candidate_data(sample([1, 2], [5, 6]))
        self.assertEqual(unique_anchor_order(rec, regions["A"])["unambiguous_anchors"], 0)

    def test_reversed_control(self):
        rec, regions = candidate_data(sample([1, 2, 3, 4], [4, 3, 2, 1]))
        a = unique_anchor_order(rec, regions["A"])
        self.assertEqual(a["adjacent_ascending"], 0)
        self.assertEqual(a["adjacent_descending"], 3)

    def test_metadata_only_aggregate(self):
        d = analyze_samples({"M_MAP01.MAP": sample([6, 7], [7, 6]),
                             "M_MAP02.MAP": sample([8, 9], [8, 9])})
        self.assertEqual(d["map_count"], 2)
        self.assertEqual(d["unambiguous_anchor_count"], 4)
        self.assertEqual(d["anchor_adjacent_ascending"], 1)
        self.assertEqual(d["anchor_adjacent_descending"], 1)
        self.assertEqual(d["matches_by_region_and_record_field"]["A"][1], 4)
        self.assertNotIn("record_positions", str(d))

    def test_reject_invalid_inputs(self):
        with self.assertRaises(ValueError):
            candidate_data(bytes(MAP_BYTES - 1))
        with self.assertRaises(ValueError):
            multiset_match_table([], {"A": [1]})
        with self.assertRaises(ValueError):
            multiset_match_table([(1, 2, 3, 4, 5, 6)], {"A": []})
        with self.assertRaises(ValueError):
            unique_anchor_order([(1, 2, 3, 4, 5, 6)], [2], 10)
        with self.assertRaises(ValueError):
            analyze_samples({})
        with self.assertRaises(ValueError):
            analyze_samples({"BAD.DAT": sample([1], [1])})

    def test_empty_layer(self):
        d = analyze_samples({"M_MAP01.MAP": sample([1, 2], [])})
        self.assertEqual(d["nonzero_word_counts"]["A"], 0)
        self.assertIsNone(d["a_field_1_overlap_fraction"])
        self.assertIsNone(d["anchor_ascending_fraction"])


if __name__ == "__main__":
    unittest.main()
