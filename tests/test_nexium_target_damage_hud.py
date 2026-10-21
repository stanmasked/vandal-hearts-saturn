"""Stage58 synthetic/adversarial image checks; not NeXium guest evidence."""
from __future__ import annotations
import unittest
from PIL import ImageDraw
from test_nexium_enemy_attack_cue import synthetic
from tools.nexium_selected_unit_hud import DIGITS,DARK,WHITE
from tools.nexium_target_damage_hud import expect_visible,expect_hidden,GOLD


def frame(damage=None,*,lethal=False,spent=False,wrong_ko=False,offset=0):
    state="spent" if spent else "ready" if damage is not None else "inspect"
    im=synthetic(state)
    if damage is None:return im
    d=ImageDraw.Draw(im)
    # DMG label D first glyph, pixel sampled at (1091,676).
    d.rectangle((1090,675,1091,676),fill=WHITE)
    for i,digit in enumerate(str(damage)):
        for y,mask in enumerate(DIGITS[digit]):
            for x in range(3):
                if mask & (1 << (2-x)):
                    xx=1122+8*i+2*x
                    yy=675+2*y+offset
                    d.rectangle((xx,yy,xx+1,yy+1),fill=WHITE)
    if lethal or wrong_ko:
        d.rectangle((1188,675,1189,676),fill=GOLD)
    return im

class DamageDigits(unittest.TestCase):
    def test_first_strike_damage_six(self):
        self.assertTrue(expect_visible(frame(6),6))
    def test_lethal_damage_two(self):
        self.assertTrue(expect_visible(frame(2,lethal=True),2,lethal=True))
    def test_scaled_guest_y_shift(self):
        self.assertTrue(expect_visible(frame(6,offset=-2),6))
    def test_forged_damage_rejected(self):
        with self.assertRaisesRegex(ValueError,"numeral mismatch"):
            expect_visible(frame(2),6)
    def test_forged_six_as_two_rejected(self):
        with self.assertRaisesRegex(ValueError,"numeral mismatch"):
            expect_visible(frame(6),2)
    def test_missing_lethal_ko_rejected(self):
        with self.assertRaisesRegex(ValueError,"ko"):
            expect_visible(frame(2),2,lethal=True)
    def test_forged_ko_on_regular_hit_rejected(self):
        with self.assertRaisesRegex(ValueError,"ko"):
            expect_visible(frame(6,wrong_ko=True),6)
    def test_no_selection_hides_damage(self):
        self.assertTrue(expect_hidden(synthetic("inspect"),enemy_visible=True))
    def test_used_action_hides_damage(self):
        self.assertTrue(expect_hidden(synthetic("spent"),enemy_visible=True))
    def test_terminal_hides_damage(self):
        self.assertTrue(expect_hidden(synthetic("hidden"),enemy_visible=False))
    def test_wrong_ghost_digit_after_attack_rejected(self):
        with self.assertRaisesRegex(ValueError,"label"):
            expect_hidden(frame(6,spent=True),enemy_visible=True)
    def test_missing_damage_label_rejected(self):
        im=frame(6)
        ImageDraw.Draw(im).rectangle((1090,675,1091,676),fill=DARK)
        with self.assertRaisesRegex(ValueError,"label"):
            expect_visible(im,6)

if __name__=="__main__":unittest.main()
