"""Stage60 synthetic / adversarial bar tests, not evidence of guest NeXium."""
from __future__ import annotations
import unittest
from PIL import ImageDraw

from test_nexium_enemy_attack_cue import synthetic
from tools.nexium_target_health_bar import verify_colors,GREEN,RED
from tools.nexium_selected_unit_hud import DARK

def frame(current=None,after=None,*,forged=None,spent=False):
    im=synthetic("spent" if spent else "ready" if current is not None else "inspect")
    if current is not None:
        draw=ImageDraw.Draw(im)
        width=220*after//current
        draw.rectangle((1020,705,1239,709),fill=RED)
        if width:draw.rectangle((1020,705,1019+width,709),fill=GREEN)
    if forged:
        x,color=forged
        ImageDraw.Draw(im).rectangle((x,705,x+4,709),fill=color)
    return im

class ProjectedHealthBar(unittest.TestCase):
    def test_initial_14_of_20(self):
        self.assertTrue(verify_colors(frame(20,14),current_hp=20,hp_after=14))
    def test_second_8_of_14(self):
        self.assertTrue(verify_colors(frame(14,8),current_hp=14,hp_after=8))
    def test_third_2_of_8(self):
        self.assertTrue(verify_colors(frame(8,2),current_hp=8,hp_after=2))
    def test_lethal_zero_of_two(self):
        self.assertTrue(verify_colors(frame(2,0),current_hp=2,hp_after=0))
    def test_hidden_no_selection(self):
        self.assertTrue(verify_colors(frame(),enemy_visible=True))
    def test_hidden_after_attack(self):
        self.assertTrue(verify_colors(frame(None,None,spent=True),enemy_visible=True))
    def test_hidden_terminal(self):
        self.assertTrue(verify_colors(synthetic("hidden")))
    def test_forged_lethal_green_fails(self):
        with self.assertRaisesRegex(ValueError,"projected bar mismatch"):
            verify_colors(frame(2,0,forged=(1100,GREEN)),current_hp=2,hp_after=0)
    def test_forged_first_damage_fails(self):
        with self.assertRaisesRegex(ValueError,"projected bar mismatch"):
            verify_colors(frame(20,14,forged=(1100,RED)),current_hp=20,hp_after=14)
    def test_forged_first_remaining_fails(self):
        with self.assertRaisesRegex(ValueError,"projected bar mismatch"):
            verify_colors(frame(20,14,forged=(1200,GREEN)),current_hp=20,hp_after=14)
    def test_forged_nonvisible_bar_fails(self):
        with self.assertRaisesRegex(ValueError,"ghost projected"):
            verify_colors(frame(None,None,forged=(1100,RED)),enemy_visible=True)
    def test_forged_bar_when_spent_fails(self):
        with self.assertRaisesRegex(ValueError,"ghost projected"):
            verify_colors(frame(None,None,spent=True,forged=(1100,GREEN)),enemy_visible=True)
    def test_invalid_current_hp_fails(self):
        with self.assertRaisesRegex(ValueError,"invalid legal"):
            verify_colors(frame(20,14),current_hp=0,hp_after=14)
    def test_invalid_overhealed_preview_fails(self):
        with self.assertRaisesRegex(ValueError,"invalid legal"):
            verify_colors(frame(20,14),current_hp=20,hp_after=21)

if __name__=="__main__":
    unittest.main()
