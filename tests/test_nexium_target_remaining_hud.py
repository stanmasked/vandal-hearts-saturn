"""Stage59 synthetic/adversarial bitmap tests; NOT real NeXium evidence."""
from __future__ import annotations
import unittest
from PIL import ImageDraw

from test_nexium_enemy_attack_cue import synthetic
from tools.nexium_target_remaining_hud import expect_visible,expect_hidden
from tools.nexium_selected_unit_hud import DIGITS, WHITE, DARK

def frame(hp=None,*,offset_y=0,shift_x=0,spent=False):
    picture=synthetic("spent" if spent else "ready" if hp is not None else "inspect")
    if hp is None:return picture
    drawer=ImageDraw.Draw(picture)
    for x in (1140,1148):
        drawer.rectangle((x,675,x+1,676),fill=WHITE)
    for i,ch in enumerate(str(hp)):
        for y,mask in enumerate(DIGITS[ch]):
            for x in range(3):
                if mask & (1 << (2-x)):
                    px=1164+8*i+2*x+shift_x
                    py=675+2*y+offset_y
                    drawer.rectangle((px,py,px+1,py+1),fill=WHITE)
    return picture

class RemainingHpPixels(unittest.TestCase):
    def test_first_strike_hp14(self):
        self.assertTrue(expect_visible(frame(14),14))
    def test_after_second_strike_hp8(self):
        self.assertTrue(expect_visible(frame(8),8))
    def test_after_third_strike_hp2(self):
        self.assertTrue(expect_visible(frame(2),2))
    def test_final_strike_hp_zero(self):
        self.assertTrue(expect_visible(frame(0),0))
    def test_scaled_shift(self):
        self.assertTrue(expect_visible(frame(14,offset_y=-2,shift_x=-1),14))
    def test_forged_after_hit_hp_rejected(self):
        with self.assertRaisesRegex(ValueError,"bitmap mismatch"):
            expect_visible(frame(14),8)
    def test_forged_lethal_hp_rejected(self):
        with self.assertRaisesRegex(ValueError,"bitmap mismatch"):
            expect_visible(frame(2),0)
    def test_forged_zero_as_two_rejected(self):
        with self.assertRaisesRegex(ValueError,"bitmap mismatch"):
            expect_visible(frame(0),2)
    def test_enemy_visible_no_selection_hides_readout(self):
        self.assertTrue(expect_hidden(frame(None),enemy_visible=True))
    def test_hidden_terminal(self):
        self.assertTrue(expect_hidden(synthetic("hidden"),enemy_visible=False))
    def test_ghost_still_visible_after_spent_rejected(self):
        with self.assertRaisesRegex(ValueError,"pixel mismatch"):
            expect_hidden(frame(14,spent=True),enemy_visible=True)
    def test_wrong_label_color_rejected(self):
        bad=frame(14)
        ImageDraw.Draw(bad).rectangle((1140,675,1141,676),fill=DARK)
        with self.assertRaisesRegex(ValueError,"pixel mismatch"):
            expect_visible(bad,14)

if __name__=="__main__":unittest.main()
