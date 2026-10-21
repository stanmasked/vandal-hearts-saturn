"""Stage 14: synthetic-only controls. No copyrighted game bytes."""
from __future__ import annotations
import unittest
from tools.saturn_map_ab_blocked import (
    fold_for_row, evaluate, analyze_samples, rates,
    PITCH, ROWS, SPLITS, SHIFTS,
)
from tools.saturn_map_ab_prediction import MAP_BYTES, TAIL_START, LAYER_WORDS


def make_map(a: list[int], b: list[int]) -> bytes:
    if len(a) > LAYER_WORDS or len(b) > LAYER_WORDS:
        raise ValueError('Oversized fixture')
    data = bytearray(MAP_BYTES)
    for i, value in enumerate(a):
        data[TAIL_START + 2 * i:TAIL_START + 2 * i + 2] = value.to_bytes(2, 'big')
    for i, value in enumerate(b):
        at = TAIL_START + 2 * (i + LAYER_WORDS)
        data[at:at + 2] = value.to_bytes(2, 'big')
    return bytes(data)


class BlockedABTests(unittest.TestCase):
    def test_contiguous_folds(self):
        self.assertEqual([fold_for_row(i, 4, 28, 'blocked') for i in range(28)],
                         [0] * 7 + [1] * 7 + [2] * 7 + [3] * 7)

    def test_interleaved_folds(self):
        self.assertEqual([fold_for_row(i, 4, 28, 'interleaved') for i in range(8)],
                         [0, 1, 2, 3] * 2)

    def test_reject_unknown_folds(self):
        for call in (lambda: fold_for_row(28, 4, 28, 'blocked'),
                     lambda: fold_for_row(0, 1, 28, 'blocked'),
                     lambda: fold_for_row(0, 4, 28, 'unknown')):
            with self.assertRaises(ValueError):
                call()

    def test_perfect_structural_mapping_both_splits(self):
        a, b = [1, 2] * (LAYER_WORDS // 2), [11, 12] * (LAYER_WORDS // 2)
        for split in SPLITS:
            d = evaluate(a, b, split)
            self.assertEqual(d['model_correct'], LAYER_WORDS)
            self.assertEqual(d['test_nonzero'], LAYER_WORDS)
            self.assertEqual(d['covered'], LAYER_WORDS)

    def test_row_leakage_is_forbidden(self):
        a = [0] * (4 * PITCH)
        b = [0] * (4 * PITCH)
        for row in range(4):
            a[row * PITCH] = row + 1
            b[row * PITCH] = row + 101
        for split in SPLITS:
            d = evaluate(a, b, split)
            self.assertEqual(d['covered'], 0)
            self.assertEqual(d['test_nonzero'], 4)

    def test_training_fold_skip_explicit(self):
        a = [0] * (4 * PITCH)
        b = [0] * (4 * PITCH)
        a[0], b[0] = 1, 2
        for split in SPLITS:
            d = evaluate(a, b, split)
            self.assertEqual(d['folds_without_training'], 1)
            self.assertEqual(d['test_nonzero'], 0)

    def test_broad_shift_degrades_alignment(self):
        a, b = [1] * 128 + [2] * 128, [12] * 128 + [13] * 128
        for split in SPLITS:
            self.assertGreater(evaluate(a, b, split)['model_correct'],
                               evaluate(a, b, split, shift=64)['model_correct'])

    def test_zero_only_data(self):
        self.assertEqual(evaluate([0] * 256, [0] * 256)['covered'], 0)
        self.assertIsNone(rates(evaluate([0] * 256, [0] * 256))['model_accuracy_covered'])

    def test_invalid_arrays_and_parameters(self):
        a, b = [1] * 256, [2] * 256
        for call in (lambda: evaluate([], []), lambda: evaluate(a, b[:-1]),
                     lambda: evaluate(a, b, shift=-1),
                     lambda: evaluate(a, b, shift=256),
                     lambda: evaluate(a, b, folds=1),
                     lambda: evaluate(a, b, split='other'),
                     lambda: evaluate([65536] + a[1:], b)):
            with self.assertRaises(ValueError):
                call()

    def test_aggregate_counts_not_word_values(self):
        report = analyze_samples({'M_MAP01.MAP': make_map([111] * LAYER_WORDS,
                                                          [222] * LAYER_WORDS)})
        self.assertEqual(report['source_file_count'], 1)
        self.assertEqual(report['aggregate']['blocked']['0']['counts']['covered'], LAYER_WORDS)
        self.assertNotIn('111', str(report))
        self.assertNotIn('222', str(report))
        self.assertEqual(report['shift_controls_words'], list(SHIFTS))

    def test_empty_and_wrong_file(self):
        with self.assertRaises(ValueError):
            analyze_samples({})
        with self.assertRaises(ValueError):
            analyze_samples({'BAD.BIN': make_map([1], [2])})


if __name__ == '__main__':
    unittest.main()
