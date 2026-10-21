"""Stage61 synthetic/adversarial bitmap checks; not NeXium guest evidence."""
from __future__ import annotations
import unittest
from PIL import ImageDraw
from test_nexium_enemy_attack_cue import synthetic
from tools.nexium_turn_round_hud import R, expect_round, expect_hidden
from tools.nexium_selected_unit_hud import DIGITS, WHITE, DARK

def frame(n=None,*,shift_x=0,shift_y=0):
    picture=synthetic("hidden")
    if n is None:return picture
    draw=ImageDraw.Draw(picture)
    draw.rectangle((93,675,135,699),fill=DARK)
    for start,masks in [(97,R)]+[
        (113+8*i,DIGITS[d]) for i,d in enumerate(str(n))]:
        for y,mask in enumerate(masks):
            for x in range(3):
                if mask & (1 << (2-x)):
                    left=start+2*x+shift_x
                    top=681+2*y+shift_y
                    draw.rectangle((left,top,left+1,top+1),fill=WHITE)
    return picture

class RoundHudTests(unittest.TestCase):
    def test_round_one(self):
        self.assertTrue(expect_round(frame(1),1))
    def test_round_two(self):
        self.assertTrue(expect_round(frame(2),2))
    def test_round_four(self):
        self.assertTrue(expect_round(frame(4),4))
    def test_round_eight(self):
        self.assertTrue(expect_round(frame(8),8))
    def test_two_digit_round(self):
        self.assertTrue(expect_round(frame(12),12))
    def test_round_99(self):
        self.assertTrue(expect_round(frame(99),99))
    def test_guest_font_shift(self):
        self.assertTrue(expect_round(frame(4,shift_x=-1,shift_y=-2),4))
    def test_forged_two_as_one_rejected(self):
        with self.assertRaisesRegex(ValueError,"numeral mismatch"):
            expect_round(frame(2),1)
    def test_forged_four_as_two_rejected(self):
        with self.assertRaisesRegex(ValueError,"numeral mismatch"):
            expect_round(frame(4),2)
    def test_forged_extra_digit_rejected(self):
        with self.assertRaisesRegex(ValueError,"numeral mismatch"):
            expect_round(frame(12),13)
    def test_absent_badge_rejected(self):
        with self.assertRaisesRegex(ValueError,"background"):
            expect_round(frame(),1)
    def test_hidden_terminal(self):
        self.assertTrue(expect_hidden(frame()))
    def test_ghost_badge_after_victory_fails(self):
        with self.assertRaisesRegex(ValueError,"ghost round"):
            expect_hidden(frame(4))
    def test_missing_letter_rejected(self):
        image=frame(2)
        ImageDraw.Draw(image).rectangle((97,681,102,690),fill=DARK)
        with self.assertRaisesRegex(ValueError,"numeral mismatch"):
            expect_round(image,2)
    def test_invalid_counter_rejected(self):
        with self.assertRaisesRegex(ValueError,"out of display"):
            expect_round(frame(1),0)

if __name__=="__main__":
    unittest.main()
