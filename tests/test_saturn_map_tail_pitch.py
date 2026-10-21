"""Synthetic-only tests for Stage 08; do not require copyrighted disc data."""
import unittest

from tools.saturn_map_records import TAIL_START, MAP_BYTES
from tools.saturn_map_tail_pitch import (
    nonzero_tail_words, pitch_scores, summarize,
)


def make_tail(indices):
    body = bytearray(MAP_BYTES)
    for index in indices:
        at = TAIL_START + index * 2
        body[at:at + 2] = b'\x00\x01'
    return bytes(body)


class Stage08PitchTests(unittest.TestCase):
    def test_nonzero_indices(self):
        self.assertEqual(nonzero_tail_words(make_tail([0, 63, 64, 2048])),
                         {0, 63, 64, 2048})

    def test_zero_image(self):
        self.assertEqual(nonzero_tail_words(bytes(MAP_BYTES)), set())

    def test_find_64_pitch_on_synthetic_grid(self):
        points = {row * 64 + col for row in range(5) for col in range(5)}
        result = pitch_scores(points)
        self.assertEqual(result['top_lag'], 64)
        self.assertEqual(result['reference_pairs'], 20)
        self.assertEqual(result['reference_rank'], 1)
        self.assertTrue(result['reference_is_first'])

    def test_other_pitch_rejected(self):
        points = {row * 20 + col for row in range(5) for col in range(5)}
        result = pitch_scores(points)
        self.assertEqual(result['top_lag'], 20)
        self.assertFalse(result['reference_is_first'])

    def test_deterministic_tie(self):
        result = pitch_scores({1, 2, 3}, minimum=16, maximum=65)
        self.assertEqual(result['top_lag'], 16)
        self.assertEqual(result['reference_rank'], 49)

    def test_invalid_inputs(self):
        for fn in (lambda: pitch_scores(set()),
                   lambda: pitch_scores({-1}),
                   lambda: pitch_scores({0, 1}, minimum=0),
                   lambda: pitch_scores({0, 1}, maximum=50),
                   lambda: nonzero_tail_words(b''),
                   lambda: nonzero_tail_words(bytes(MAP_BYTES), 1),
                   lambda: nonzero_tail_words(bytes(MAP_BYTES), MAP_BYTES)):
            with self.assertRaises(ValueError):
                fn()

    def test_report_counts(self):
        profiles = [
            {'name': 'M_MAP01.MAP', 'family': 'M_MAP',
             'reference_is_first': True, 'reference_in_top_four': True},
            {'name': 'M_MAP02.MAP', 'family': 'M_MAP',
             'reference_is_first': False, 'reference_in_top_four': False},
            {'name': 'M_SHOW.MAP', 'family': 'M_SHOW',
             'reference_is_first': True, 'reference_in_top_four': True},
        ]
        summary = summarize(profiles)
        self.assertEqual(summary['map_count'], 3)
        self.assertEqual(summary['reference_first_count'], 2)
        self.assertEqual(summary['reference_top_four_count'], 2)
        self.assertEqual(summary['family_counts']['M_MAP']['not_in_top_four'],
                         ['M_MAP02.MAP'])

    def test_empty_summary_rejected(self):
        with self.assertRaises(ValueError):
            summarize([])


if __name__ == '__main__':
    unittest.main()
