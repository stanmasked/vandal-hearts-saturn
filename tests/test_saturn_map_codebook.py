"""Stage 16 tests: synthetic-only fixtures, no original Saturn assets."""
import json
import unittest
from collections import Counter
from tools.saturn_map_codebook import (
    PITCH, ambiguity, permute_targets, stable_seed, aggregate,
)
from tools.saturn_map_ab_prediction import TAIL_START, MAP_BYTES, LAYER_WORDS


def sample(a, b):
    assert len(a) <= LAYER_WORDS and len(b) <= LAYER_WORDS
    out = bytearray(MAP_BYTES)
    for i, value in enumerate(a):
        at = TAIL_START + 2 * i
        out[at:at+2] = value.to_bytes(2, 'big')
    for i, value in enumerate(b):
        at = TAIL_START + 2 * (LAYER_WORDS+i)
        out[at:at+2] = value.to_bytes(2, 'big')
    return bytes(out)


class CodebookTests(unittest.TestCase):
    def test_perfect_mapping_and_entropy(self):
        r = ambiguity([1, 1, 2, 2], [10, 10, 20, 20])
        self.assertEqual(r['pairs'], 4)
        self.assertEqual(r['singleton_target_a'], 2)
        self.assertEqual(r['modal_correct_in_sample'], 4)
        self.assertEqual(r['conditional_entropy_bits'], 0.0)
        self.assertEqual(r['b_entropy_bits'], 1.0)

    def test_one_to_many_mapping(self):
        r = ambiguity([1, 1, 1, 1], [10, 10, 20, 20])
        self.assertEqual(r['ambiguous_target_a'], 1)
        self.assertEqual(r['deterministic_a_pair_mass'], 0)
        self.assertEqual(r['modal_correct_in_sample'], 2)
        self.assertEqual(r['conditional_entropy_bits'], 1.0)

    def test_zero_pair_exclusion(self):
        r = ambiguity([1, 1, 0, 0], [0, 0, 10, 0])
        self.assertEqual(r['pairs'], 0)
        self.assertIsNone(r['conditional_entropy_bits'])

    def test_reject_malformed_arrays(self):
        for a,b in (([], []), ([1], [1,2]), ([65536], [2]), ([-1], [1])):
            with self.assertRaises(ValueError):
                ambiguity(a,b)

    def test_shuffles_preserve_occupancy_and_marginals(self):
        a = [1, 2, 3, 0] * 32
        b = [20, 30, 40, 50] * 32
        for kind in ('within_row', 'whole_map'):
            changed = permute_targets(a,b,kind,21)
            self.assertEqual([bool(x and y) for x,y in zip(a,b)],
                             [bool(x and y) for x,y in zip(a,changed)])
            self.assertEqual(Counter(y for x,y in zip(a,b) if x and y),
                             Counter(y for x,y in zip(a,changed) if x and y))

    def test_row_shuffle_preserves_each_row_histogram(self):
        a = [1] * 128
        b = [10] * 32 + [20] * 32 + [30] * 32 + [40] * 32
        changed = permute_targets(a,b,'within_row',13)
        self.assertEqual(Counter(changed[:64]), Counter(b[:64]))
        self.assertEqual(Counter(changed[64:]), Counter(b[64:]))

    def test_seed_reproducible(self):
        a,b = [1] * 256, list(range(256))
        self.assertEqual(permute_targets(a,b,'whole_map',stable_seed('map','whole_map',0)),
                         permute_targets(a,b,'whole_map',stable_seed('map','whole_map',0)))
        self.assertNotEqual(stable_seed('map','whole_map',0),stable_seed('map','whole_map',1))

    def test_reject_invalid_shuffle_mode(self):
        with self.assertRaises(ValueError):
            permute_targets([1] * 64,[1] * 64,'anything',5)

    def test_perfect_association_beats_shuffle_control(self):
        a = [1,2] * (LAYER_WORDS//2)
        b = [11,22] * (LAYER_WORDS//2)
        report=aggregate({'M_MAP01.MAP':sample(a,b)},permutations=4)
        actual=report['blocked_holdout']['observed']
        shuffled=report['blocked_holdout']['controls']['whole_map']
        self.assertEqual(actual['model_accuracy'],1.0)
        self.assertLess(shuffled['model_accuracy'],0.8)

    def test_noise_and_privacy_report(self):
        a=[111] * LAYER_WORDS
        b=[222] * LAYER_WORDS
        report=aggregate({'M_MAP01.MAP':sample(a,b)},permutations=2)
        text=json.dumps(report)
        self.assertNotIn('111',text)
        self.assertNotIn('222',text)
        self.assertEqual(report['codebook']['pairs'],LAYER_WORDS)
        self.assertEqual(report['codebook']['singleton_target_a'],1)

    def test_invalid_aggregate_inputs(self):
        for data,n in (({},2),({'M_MAP01.MAP':sample([1],[2])},0),
                       ({'M_MAP01.MAP':sample([1],[2])},129),
                       ({'other.txt':sample([1],[2])},2)):
            with self.assertRaises(ValueError):
                aggregate(data,permutations=n)


if __name__ == '__main__':
    unittest.main()
