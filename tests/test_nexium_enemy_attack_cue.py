"""Stage57 adversarial/synthetic frame tests, not evidence of NeXium execution."""
from __future__ import annotations
import unittest
from PIL import ImageDraw

from test_nexium_enemy_hover_hud import frame
from tools.nexium_enemy_attack_cue import COLORS, CUE, expect_cue

def synthetic(state="hidden",hp=20):
    if state not in COLORS:
        raise ValueError(state)
    picture=frame(None if state=="hidden" else hp)
    if state!="hidden":
        ImageDraw.Draw(picture).rectangle((1242,675,1265,684),fill=COLORS[state])
    return picture

class AttackCueTests(unittest.TestCase):
    def test_hidden_away_from_enemy(self):
        self.assertTrue(expect_cue(synthetic("hidden"),"hidden"))
    def test_idle_hover_not_attack_ready(self):
        self.assertTrue(expect_cue(synthetic("inspect"),"inspect"))
    def test_ready_target(self):
        self.assertTrue(expect_cue(synthetic("ready"),"ready"))
    def test_spent_action(self):
        self.assertTrue(expect_cue(synthetic("spent",14),"spent"))
    def test_out_of_range(self):
        self.assertTrue(expect_cue(synthetic("blocked"),"blocked"))
    def test_forged_ready_when_spent_fails(self):
        with self.assertRaisesRegex(ValueError,"attack cue pixel mismatch"):
            expect_cue(synthetic("ready"),"spent")
    def test_forged_idle_when_ready_fails(self):
        with self.assertRaisesRegex(ValueError,"attack cue pixel mismatch"):
            expect_cue(synthetic("inspect"),"ready")
    def test_forged_spent_when_ready_fails(self):
        with self.assertRaisesRegex(ValueError,"attack cue pixel mismatch"):
            expect_cue(synthetic("spent"),"ready")
    def test_hidden_terminal_cannot_show_old_spent(self):
        with self.assertRaisesRegex(ValueError,"attack cue pixel mismatch"):
            expect_cue(synthetic("spent"),"hidden")
    def test_hidden_terminal_cannot_show_old_ready(self):
        with self.assertRaisesRegex(ValueError,"attack cue pixel mismatch"):
            expect_cue(synthetic("ready"),"hidden")
    def test_removed_markers_are_not_accepted(self):
        test=synthetic("ready")
        ImageDraw.Draw(test).rectangle((1242,675,1265,684),fill=(23,30,41))
        with self.assertRaisesRegex(ValueError,"attack cue pixel mismatch"):
            expect_cue(test,"ready")
    def test_unknown_state_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"unknown"):
            expect_cue(synthetic("inspect"),"selected")

if __name__=="__main__":
    unittest.main()
