"""Stage 09 tests are synthetic only; they use no protected game media."""
import unittest
from tools.saturn_map_layers import SEGMENTS, words, subregion, compare_layers, profile_map, summary
from tools.saturn_map_records import TAIL_START, MAP_BYTES


def synthetic_map(a=(), b=(), d=(), same=False):
    data = bytearray(MAP_BYTES)
    for i, (row, indices) in enumerate(((0, a), (28, b), (70, d))):
        for index in indices:
            offset = TAIL_START + (row * 64 + index) * 2
            val = 33 if same else 33 + 20 * i
            data[offset:offset + 2] = val.to_bytes(2, "big")
    return bytes(data)


class LayerTests(unittest.TestCase):
    def test_segment_layout(self):
        self.assertEqual(sum(x[2] for x in SEGMENTS), 173)
        self.assertEqual([x[2] for x in SEGMENTS], [28, 28, 14, 28, 75])

    def test_mask_identity_different_values(self):
        p = profile_map(synthetic_map([0, 64, 67], [0, 64, 67], [0, 64, 67]))
        self.assertTrue(p["AB"]["mask_equal"])
        self.assertTrue(p["BD"]["mask_equal"])
        self.assertEqual(p["AB"]["overlapping_nonzero"], 3)
        self.assertEqual(p["AB"]["matching_nonzero_values"], 0)

    def test_identical_values(self):
        p = profile_map(synthetic_map([1, 2], [1, 2], same=True))
        self.assertEqual(p["AB"]["matching_nonzero_values"], 2)

    def test_mismatch(self):
        p = profile_map(synthetic_map([0, 1], [0, 2], [0, 2]))
        self.assertEqual(p["AB"]["mask_mismatch_positions"], 2)
        self.assertEqual(p["AB"]["overlapping_nonzero"], 1)

    def test_region_bounds(self):
        values = list(range(173 * 64))
        self.assertEqual(subregion(values, 28, 28)[0], 28 * 64)
        for row, n in ((-1, 2), (170, 4), (10, 0)):
            with self.assertRaises(ValueError):
                subregion(values, row, n)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            words(bytes(MAP_BYTES - 2))
        for a, b in (([], []), ([1], [1, 2])):
            with self.assertRaises(ValueError):
                compare_layers(a, b)
        with self.assertRaises(ValueError):
            summary({})

    def test_summary(self):
        samples = {"M_MAP01.MAP": profile_map(synthetic_map([1], [1])),
                   "M_MAP02.MAP": profile_map(synthetic_map([2], [3])),
                   "M_SHOW.MAP": profile_map(synthetic_map([5], [5]))}
        result = summary(samples)
        self.assertEqual(result["AB"]["maps_with_identical_occupancy"], 2)
        self.assertEqual(result["AB"]["exceptions"], ["M_MAP02.MAP"])
        self.assertEqual(result["families"]["M_SHOW"]["AB_exact"], 1)

    def test_mask_vs_value(self):
        result = compare_layers([0, 100, 200, 0], [0, 101, 201, 0])
        self.assertTrue(result["mask_equal"])
        self.assertEqual(result["matching_nonzero_values"], 0)
        self.assertEqual(result["overlapping_nonzero"], 2)


if __name__ == "__main__":
    unittest.main()
