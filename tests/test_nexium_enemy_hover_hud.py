"""Stage56 synthetic/adversarial pixel audits (NOT proof of guest NeXium)."""
from __future__ import annotations
import unittest
from PIL import ImageDraw

from test_nexium_attack_action import picture
from tools.nexium_enemy_hover_hud import expect_visible, expect_hidden, RED, PANEL
from tools.nexium_selected_unit_hud import DIGITS, DARK, HELP, WHITE


def frame(hp=None, *, corrupt=None, offset=0,
          attack=6, defense=2, attack_range=1):
    image=picture()
    draw=ImageDraw.Draw(image)
    draw.rectangle((0,660,1279,719),fill=HELP)
    if hp is None:
        return image
    draw.rectangle((1002,668,1273,711),fill=DARK)
    draw.rectangle((1008,674,1013,706),fill=RED)
    # Sampled letter bits from the same SDL 3x5 bitmap font:
    # first white top-row pixels for Raider R, H, A, D, R.
    for x,y in ((1020,675),(1022,690),(1079,690),(1140,690),(1204,690)):
        draw.rectangle((x,y,x+1,y+1),fill=WHITE)
    for start_x, value in (
        (1022+8*3,hp),(1077+8*4,attack),
        (1140+8*4,defense),(1204+8*4,attack_range)
    ):
        for index,digit in enumerate(str(value)):
            for y,mask in enumerate(DIGITS[digit]):
                for x in range(3):
                    if mask & (1 << (2-x)):
                        left=start_x+8*index+2*x
                        top=690+2*y+offset
                        draw.rectangle((left,top,left+1,top+1),fill=WHITE)
    if corrupt:
        x,y=PANEL[corrupt]
        draw.rectangle((x-1,y-1,x+1,y+1),fill=(250,150,10))
    return image


class HoverHudPixels(unittest.TestCase):
    def test_no_target_is_hidden(self):
        self.assertTrue(expect_hidden(frame()))
    def test_enemy_hp20(self):
        self.assertTrue(expect_visible(frame(20),20))
    def test_enemy_hp14(self):
        self.assertTrue(expect_visible(frame(14),14))
    def test_enemy_hp8(self):
        self.assertTrue(expect_visible(frame(8),8))
    def test_enemy_hp2(self):
        self.assertTrue(expect_visible(frame(2),2))
    def test_scaled_offset(self):
        self.assertTrue(expect_visible(frame(14,offset=-2),14))
    def test_forged_hp_rejected(self):
        with self.assertRaisesRegex(ValueError,"HP digit mismatch"):
            expect_visible(frame(20),14)
    def test_forged_14_as_8_rejected(self):
        with self.assertRaisesRegex(ValueError,"HP digit mismatch"):
            expect_visible(frame(14),8)
    def test_forged_attack_number_rejected(self):
        with self.assertRaisesRegex(ValueError,"ATK digit mismatch"):
            expect_visible(frame(20,attack=7),20)
    def test_forged_defense_number_rejected(self):
        with self.assertRaisesRegex(ValueError,"DEF digit mismatch"):
            expect_visible(frame(14,defense=3),14)
    def test_forged_range_number_rejected(self):
        with self.assertRaisesRegex(ValueError,"RNG digit mismatch"):
            expect_visible(frame(8,attack_range=2),8)
    def test_missing_title_rejected(self):
        with self.assertRaisesRegex(ValueError,"name"):
            expect_visible(frame(20,corrupt="name"),20)
    def test_missing_attack_label_rejected(self):
        with self.assertRaisesRegex(ValueError,"attack"):
            expect_visible(frame(20,corrupt="attack"),20)
    def test_wrong_enemy_marker_rejected(self):
        with self.assertRaisesRegex(ValueError,"marker"):
            expect_visible(frame(14,corrupt="marker"),14)
    def test_ghost_enemy_panel_rejected(self):
        with self.assertRaisesRegex(ValueError,"enemy HUD pixel mismatch"):
            expect_hidden(frame(20))


if __name__=="__main__":
    unittest.main()
