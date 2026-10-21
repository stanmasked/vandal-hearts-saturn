"""Stage64 adversarial tests for the real-NeXium move-preview auditor."""
from __future__ import annotations
import unittest
from PIL import ImageDraw
from test_nexium_attack_action import picture
from tools.nexium_movement_preview_hud import expect_visible, expect_hidden
from tools.nexium_movement_preview_hud import PANEL, GREEN, WHITE, GLYPHS, TEXT_X, TEXT_Y


def movement_frame(*, visible=True, cursor=(480, 236), selected=True, cost=1,
                   remaining=3, shift_y=-2, forged=None):
    image = picture(cursor=cursor, selected=selected)
    if not visible:
        return image
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 600, 205, 641), fill=PANEL)
    draw.rectangle((22, 604, 27, 637), fill=GREEN)
    for i, char in enumerate(f"COST {cost} LEFT {remaining}"):
        for y, mask in enumerate(GLYPHS[char]):
            for x in range(3):
                if mask & (1 << (2-x)):
                    left, top = TEXT_X + 8*i + 2*x, TEXT_Y + 2*y + shift_y
                    draw.rectangle((left, top, left+1, top+1), fill=WHITE)
    if forged is not None:
        x, y, rgb = forged
        draw.point((x, y), fill=rgb)
    return image


class MovementPreviewHudTests(unittest.TestCase):
    def test_exact_legal_cost_and_remaining_glyph(self):
        self.assertTrue(expect_visible(movement_frame(), cost=1, remaining=3))
    def test_two_digit_costs_are_supported(self):
        self.assertTrue(expect_visible(movement_frame(cost=12, remaining=34),
                                       cost=12, remaining=34))
    def test_wrong_cost_rejected(self):
        with self.assertRaisesRegex(ValueError, "glyph mismatch"):
            expect_visible(movement_frame(), cost=2, remaining=3)
    def test_wrong_remaining_rejected(self):
        with self.assertRaisesRegex(ValueError, "glyph mismatch"):
            expect_visible(movement_frame(), cost=1, remaining=2)
    def test_hidden_when_selection_or_legal_tile_missing(self):
        self.assertTrue(expect_hidden(movement_frame(visible=False, selected=False)))
        self.assertTrue(expect_hidden(movement_frame(visible=False, cursor=(480, 256))))
    def test_ghost_panel_rejected(self):
        with self.assertRaisesRegex(ValueError, "ghost movement preview"):
            expect_hidden(movement_frame())
    def test_missing_panel_marker_rejected(self):
        image = movement_frame()
        ImageDraw.Draw(image).point((24, 620), fill=PANEL)
        with self.assertRaisesRegex(ValueError, "marker missing"):
            expect_visible(image)
    def test_single_physical_pixel_corruption_rejected(self):
        image = movement_frame(forged=(37, 608, PANEL))
        with self.assertRaisesRegex(ValueError, "glyph mismatch"):
            expect_visible(image)
    def test_unsupported_values_rejected_and_two_digit_fields_fit(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            expect_visible(movement_frame(), cost=100, remaining=3)
        self.assertTrue(expect_visible(movement_frame(cost=99, remaining=99),
                                       cost=99, remaining=99))


if __name__ == "__main__":
    unittest.main()
