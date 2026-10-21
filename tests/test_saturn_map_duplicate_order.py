"""ROM-free tests for Stage 12. No original Sega Saturn data is used."""
import unittest
from tools.saturn_map_duplicate_order import (
    analyze_samples, longest_increasing_anchors, sequence_diagnostics,
    unique_value_anchors,
)
from tools.saturn_map_records import MAP_BYTES, START, TAIL_START


def synthetic_map(records, layer):
    blob = bytearray(MAP_BYTES)
    for i, value in enumerate(records):
        for field, number in enumerate((326, value, 192, 0, 400, 2)):
            off = START + 12 * i + 2 * field
            blob[off:off + 2] = number.to_bytes(2, "big")
    for i, value in enumerate(layer):
        off = TAIL_START + i * 2
        blob[off:off + 2] = value.to_bytes(2, "big")
    return bytes(blob)


class Stage12Tests(unittest.TestCase):
    def test_unique_anchors(self):
        self.assertEqual(unique_value_anchors([1, 2, 2, 3], [3, 1, 2, 2]),
                         [(0, 3), (1, 0)])

    def test_increasing_chain(self):
        anchors = [(0, 1), (1, 3), (2, 2), (3, 4)]
        chosen = longest_increasing_anchors(anchors)
        self.assertEqual(len(chosen), 3)
        self.assertTrue(all(x[1] < y[1] for x, y in zip(chosen, chosen[1:])))

    def test_reverse_order_falsifies_monotonicity(self):
        result = sequence_diagnostics([10, 20, 30], [30, 20, 10])
        self.assertEqual(result['unique_in_both_anchors'], 3)
        self.assertEqual(result['max_increasing_anchor_chain'], 1)
        self.assertEqual(result['anchors_excluded_by_monotone_chain'], 2)
        self.assertTrue(result['global_monotone_anchor_hypothesis_contradicted'])

    def test_duplicate_values_have_no_global_unique_anchor(self):
        result = sequence_diagnostics([7, 7, 7], [7, 7])
        self.assertEqual(result['multiple_record_candidates'], 2)
        self.assertEqual(result['unique_in_both_anchors'], 0)
        self.assertEqual(result['hypothetical_single_candidate_duplicates'], 0)

    def test_missing_matches_and_record_singletons(self):
        r = sequence_diagnostics([10, 20, 20], [10, 20, 99, 20])
        self.assertEqual(r['layer_nonzero'], 4)
        self.assertEqual(r['no_equal_record_value'], 1)
        self.assertEqual(r['single_record_candidate'], 1)
        self.assertEqual(r['multiple_record_candidates'], 2)
        self.assertEqual(r['unique_in_both_anchors'], 1)

    def test_duplicate_can_be_conditionally_narrowed_between_anchors(self):
        r = sequence_diagnostics([10, 7, 20, 7, 30], [10, 7, 20, 7, 30])
        self.assertEqual(r['unique_in_both_anchors'], 3)
        self.assertEqual(r['max_increasing_anchor_chain'], 3)
        self.assertEqual(r['hypothetical_single_candidate_duplicates'], 2)
        self.assertEqual(r['conditional_collision_free_positions'], 2)
        self.assertEqual(r['conditional_record_collision_positions'], 0)

    def test_multiple_layer_occurrences_cannot_claim_one_record(self):
        r = sequence_diagnostics([10, 7, 20, 7, 30], [10, 7, 7, 20, 7, 30])
        self.assertEqual(r['hypothetical_single_candidate_duplicates'], 3)
        self.assertEqual(r['conditional_record_collision_positions'], 2)
        self.assertEqual(r['conditional_collision_free_positions'], 1)

    def test_globally_unique_record_is_not_unique_anchor_if_layer_repeats(self):
        r = sequence_diagnostics([7, 20], [7, 7, 20])
        self.assertEqual(r['single_record_candidate'], 3)
        self.assertEqual(r['unique_in_both_anchors'], 1)

    def test_no_layer_values(self):
        r = sequence_diagnostics([5, 6], [0, 0])
        self.assertEqual(r['layer_nonzero'], 0)
        self.assertEqual(r['unique_in_both_anchors'], 0)

    def test_invalid_inputs(self):
        for call in (lambda: unique_value_anchors([], [1]),
                     lambda: unique_value_anchors([1], []),
                     lambda: sequence_diagnostics([65536], [1]),
                     lambda: sequence_diagnostics([2], [-1]),
                     lambda: longest_increasing_anchors([(1, 0), (0, 1)]),
                     lambda: longest_increasing_anchors([(0, 1), (1, 1)]),
                     lambda: analyze_samples({}),
                     lambda: analyze_samples({'DATA.BIN': synthetic_map([1], [1])})):
            with self.assertRaises(ValueError):
                call()

    def test_synthetic_file_report_no_values_or_locations(self):
        report = analyze_samples({'M_MAP01.MAP': synthetic_map([501, 502], [501, 502])})
        self.assertEqual(report['summary']['map_count'], 1)
        self.assertEqual(report['summary']['unique_in_both_anchors'], 2)
        self.assertEqual(report['summary']['anchors_excluded_by_monotone_chain'], 0)
        self.assertEqual(report['summary']['no_equal_record_value'], 0)
        self.assertNotIn('record_indices', str(report))
        self.assertNotIn('501', str(report))

    def test_no_unsupported_positional_claim(self):
        r = sequence_diagnostics([10, 20, 30], [10, 30, 20])
        self.assertTrue(r['global_monotone_anchor_hypothesis_contradicted'])
        self.assertLess(r['max_increasing_anchor_chain'], r['unique_in_both_anchors'])


if __name__ == '__main__':
    unittest.main()
