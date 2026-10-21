"""Stage72 Python reference digest tests, all synthetic (no game media)."""
import unittest

from tools.check_terrain_matrix import invented_cell
from tools.check_terrain_order import (
    independent_case_digest, ordered_digest, swap_fields,
)
from tools.saturn_terrain_bridge import export_numeric_terrain
from tools.check_terrain_matrix import make_case


class OrderedTerrainDigestTests(unittest.TestCase):
    def test_known_dimensions_produce_distinct_digests(self):
        self.assertNotEqual(independent_case_digest(1, 4),
                            independent_case_digest(2, 2))

    def test_order_changes_even_when_all_sums_preserved(self):
        width, height = 7, 13
        before = [invented_cell(x, y, width, height)
                  for y in range(height) for x in range(width)]
        changed = [dict(tile) for tile in before]
        for field in ("elevation", "movement_cost", "traversable"):
            changed = [dict(tile) for tile in before]
            a, b = 0, next(i for i, t in enumerate(changed)
                           if t[field] != changed[0][field])
            changed[a][field], changed[b][field] = (
                changed[b][field], changed[a][field]
            )
            self.assertNotEqual(ordered_digest(width, height, before),
                                ordered_digest(width, height, changed))

    def test_invalid_cell_order_is_rejected(self):
        cells = [invented_cell(x, y, 2, 2) for y in range(2) for x in range(2)]
        cells[0], cells[1] = cells[1], cells[0]
        with self.assertRaisesRegex(ValueError, "unordered"):
            ordered_digest(2, 2, cells)

    def test_missing_tile_rejected(self):
        cells = [invented_cell(x, y, 2, 2) for y in range(2) for x in range(2)]
        with self.assertRaisesRegex(ValueError, "incomplete"):
            ordered_digest(2, 2, cells[:3])

    def test_payload_swap_preserves_coordinates(self):
        original = export_numeric_terrain(make_case(7, 13))
        changed = swap_fields(original, 0, 1, (3, 4, 5))
        a = original.splitlines()[2:4]
        b = changed.splitlines()[2:4]
        self.assertEqual([line.split()[:3] for line in a],
                         [line.split()[:3] for line in b])
        self.assertNotEqual(original, changed)


if __name__ == "__main__":
    unittest.main()
