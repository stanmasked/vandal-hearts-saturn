"""Stage64 synthetic/adversarial pixel checks; real guest frames are audited separately."""
from __future__ import annotations

import unittest
from PIL import Image, ImageDraw

from tools.nexium_move_preview_hud import (
    GOLD, X, Y, GLYPHS, expect_hidden, expect_move_preview,
)
from tools.nexium_selected_unit_hud import DARK, HELP


def frame(*, selected=True, text=None, shift_y=0):
    image = Image.new("RGB", (1280, 720), HELP)
    draw = ImageDraw.Draw(image)
    if selected:
        draw.rectangle((350, 668, 993, 711), fill=DARK)
    if text is not None:
        for i, char in enumerate(text):
            for y, mask in enumerate(GLYPHS.get(char, (0,0,0,0,0))):
                for x in range(3):
                    if mask & (1 << (2-x)):
                        left = X + 8*i + 2*x
                        top = Y + 2*y + shift_y
                        draw.rectangle((left, top, left+1, top+1), fill=GOLD)
    return image


class MovePreviewHudPixelTests(unittest.TestCase):
    def test_exact_cost_and_remaining_budget(self):
        self.assertTrue(expect_move_preview(frame(text="COST 2 LEFT 2"), 2, 2))

    def test_bounded_guest_vertical_shift(self):
        self.assertTrue(expect_move_preview(frame(text="COST 2 LEFT 2", shift_y=-2), 2, 2))

    def test_wrong_path_cost_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "bitmap mismatch"):
            expect_move_preview(frame(text="COST 2 LEFT 2"), 1, 2)

    def test_wrong_remaining_budget_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "bitmap mismatch"):
            expect_move_preview(frame(text="COST 2 LEFT 2"), 2, 3)

    def test_missing_label_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "bitmap mismatch"):
            expect_move_preview(frame(), 2, 2)

    def test_one_sampled_physical_pixel_corruption_is_rejected(self):
        image = frame(text="COST 2 LEFT 2")
        ImageDraw.Draw(image).point((502, 670), fill=DARK)
        with self.assertRaisesRegex(ValueError, "bitmap mismatch"):
            expect_move_preview(image, 2, 2)

    def test_hidden_without_selection(self):
        self.assertTrue(expect_hidden(frame(selected=False), selected=False))

    def test_ghost_label_without_selection_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ghost movement preview"):
            expect_hidden(frame(selected=False, text="COST 2 LEFT 2"), selected=False)

    def test_hidden_after_move(self):
        self.assertTrue(expect_hidden(frame(selected=True), selected=True))

    def test_ghost_label_after_move_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ghost movement preview"):
            expect_hidden(frame(selected=True, text="COST 2 LEFT 2"), selected=True)

    def test_unsupported_values_are_rejected_not_truncated(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            expect_move_preview(frame(text="COST 2 LEFT 2"), 1000, 0)
        with self.assertRaisesRegex(ValueError, "unsupported"):
            expect_move_preview(frame(text="COST 2 LEFT 2"), 2, -1)

    def test_text_width_guard(self):
        from tools.nexium_move_preview_hud import _bits
        with self.assertRaisesRegex(ValueError, "unsupported movement preview text width"):
            _bits("COST 1000 LEFT 1000")


if __name__ == "__main__":
    unittest.main()
