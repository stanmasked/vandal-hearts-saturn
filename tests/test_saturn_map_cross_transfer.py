"""Stage 15 — synthetic-only cross-file controls (no original Saturn data)."""
import unittest
from collections import Counter

from tools.saturn_map_cross_transfer import (
    analyze_pairs, analyze_samples, candidate_pair_counts, mode, train_test, rates,
    SCOPES,
)
from tools.saturn_map_ab_prediction import MAP_BYTES, TAIL_START, LAYER_WORDS


def fixture(pairs):
    if len(pairs) > LAYER_WORDS:
        raise ValueError('Synthetic array overflow')
    raw = bytearray(MAP_BYTES)
    for i, (x, y) in enumerate(pairs):
        raw[TAIL_START + i * 2:TAIL_START + i * 2 + 2] = x.to_bytes(2, 'big')
        at = TAIL_START + (LAYER_WORDS + i) * 2
        raw[at:at + 2] = y.to_bytes(2, 'big')
    return bytes(raw)


class CrossMapTests(unittest.TestCase):
    def test_counter_from_map_excludes_zero(self):
        self.assertEqual(candidate_pair_counts(fixture([(5, 7), (5, 7), (0, 8), (6, 0)])),
                         Counter({(5, 7): 2}))

    def test_mode_tie_deterministic(self):
        self.assertEqual(mode(Counter({7: 2, 3: 2})), 3)
        with self.assertRaises(ValueError):
            mode(Counter())

    def test_leave_one_out_never_trains_on_target(self):
        pairs = {
            'M_MAP01.MAP': Counter({(1, 11): 8}),
            'M_MAP02.MAP': Counter({(1, 22): 8}),
        }
        report = analyze_pairs(pairs)
        self.assertEqual(report['maps']['M_MAP01.MAP']['results']['same_family']['covered'], 8)
        self.assertEqual(report['maps']['M_MAP01.MAP']['results']['same_family']['model_correct'], 0)
        self.assertEqual(report['maps']['M_MAP02.MAP']['results']['same_family']['model_correct'], 0)
        self.assertEqual(report['overall']['same_family']['counts']['test_nonzero'], 16)

    def test_singleton_family_skipped(self):
        pairs = {'M_SHOW.MAP': Counter({(4, 5): 3}),
                 'M_MAP01.MAP': Counter({(4, 5): 5})}
        report = analyze_pairs(pairs)
        own = report['maps']['M_SHOW.MAP']['results']['same_family']
        self.assertEqual(own['skipped_maps'], 1)
        self.assertEqual(own['skipped_nonzero'], 3)
        self.assertEqual(own['test_nonzero'], 0)
        self.assertEqual(report['maps']['M_SHOW.MAP']['results']['other_families']['model_correct'], 3)

    def test_outside_family_does_not_contain_same_family(self):
        pairs = {'M_KEY01.MAP': Counter({(1, 10): 3}),
                 'M_KEY02.MAP': Counter({(1, 10): 2}),
                 'M_MAP01.MAP': Counter({(1, 20): 4})}
        r = analyze_pairs(pairs)['maps']['M_KEY01.MAP']['results']
        self.assertEqual(r['same_family']['model_correct'], 3)
        self.assertEqual(r['other_families']['model_correct'], 0)
        self.assertEqual(r['all_other']['model_correct'], 0)  # OTHER map has majority weight

    def test_baseline_is_on_covered_sample(self):
        test = Counter({(1, 30): 2, (2, 10): 4})
        train = Counter({(1, 30): 3, (5, 10): 10})
        result = train_test(test, train)
        self.assertEqual(result['test_nonzero'], 6)
        self.assertEqual(result['covered'], 2)
        self.assertEqual(result['model_correct'], 2)
        self.assertEqual(result['baseline_correct_covered'], 0)
        self.assertEqual(result['baseline_correct_all'], 4)

    def test_all_three_scopes_and_numeric_only(self):
        pairs = {'M_IVE01.MAP': Counter({(111, 222): 5}),
                 'M_IVE02.MAP': Counter({(111, 222): 4}),
                 'M_KEY01.MAP': Counter({(111, 223): 3})}
        report = analyze_pairs(pairs)
        self.assertEqual(report['scopes'], list(SCOPES))
        self.assertEqual(report['map_count'], 3)
        self.assertNotIn('111', str(report))
        self.assertNotIn('222', str(report))
        self.assertNotIn('223', str(report))

    def test_no_training_skipped_not_falsely_successful(self):
        r = train_test(Counter({(1, 2): 10}), Counter())
        self.assertEqual(r['skipped_maps'], 1)
        self.assertEqual(r['skipped_nonzero'], 10)
        self.assertEqual(r['evaluated_maps'], 0)
        self.assertIsNone(rates(r)['model_accuracy_covered'])

    def test_invalid_training_values_and_empty(self):
        with self.assertRaises(ValueError):
            train_test(Counter({(1, 2): 1}), Counter({(0, 3): 1}))
        with self.assertRaises(ValueError):
            train_test(Counter({(1, 2): -1}), Counter({(1, 2): 2}))
        with self.assertRaises(ValueError):
            analyze_pairs({})
        with self.assertRaises(ValueError):
            analyze_pairs({'WRONG.BIN': Counter({(1, 2): 1})})

    def test_full_synthetic_file_path(self):
        samples = {'M_MAP01.MAP': fixture([(1, 2), (1, 2)]),
                   'M_MAP02.MAP': fixture([(1, 2)])}
        report = analyze_samples(samples)
        self.assertEqual(report['overall']['same_family']['counts']['model_correct'], 3)

    def test_outside_family_control_on_unseen_words(self):
        pairs = {'M_KEY01.MAP': Counter({(8, 10): 2}),
                 'M_MAP01.MAP': Counter({(9, 10): 5})}
        r = analyze_pairs(pairs)['maps']['M_KEY01.MAP']['results']['other_families']
        self.assertEqual(r['test_nonzero'], 2)
        self.assertEqual(r['covered'], 0)
        self.assertIsNone(rates(r)['model_accuracy_covered'])


if __name__ == '__main__':
    unittest.main()
