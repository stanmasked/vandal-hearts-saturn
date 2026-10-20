"""Synthetic adversarial screenshot tests for Stage52 real NeXium Defeat gate."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import ImageDraw

from test_nexium_attack_action import FakeIO, picture
from tools.nexium_duel_defeat import (
    ROUND_HASHES, SCOUT_HP, _hp, exercise, verify_folder,
)


def frame(index, *, cursor=(520,276), scout_hp=None, effect=None,
          scout_body=None, raider_body=True):
    value = SCOUT_HP[index] if scout_hp is None else scout_hp
    if scout_body is None:
        scout_body = value > 0
    image = picture(cursor=cursor,state=ROUND_HASHES[index],hp=20,effect=effect)
    draw = ImageDraw.Draw(image)
    draw.rectangle((463,195,496,199),fill=(31,32,32))
    if value > 0:
        width=max(1,min(34,value*34//26))
        draw.rectangle((463,195,463+width-1,199),fill=(117,221,109))
    if scout_body:
        draw.rectangle((472,220,489,242),fill=(63,167,239))
    if raider_body:
        draw.rectangle((512,239,529,254),fill=(239,79,76))
    return image


class DefeatTests(unittest.TestCase):
    def setUp(self):
        self.initial = frame(0,cursor=(480,256))
        self.after_right = frame(0)
        self.rounds = [frame(i,effect="TurnEnded") for i in range(1,9)]
        self.blocked = [frame(8,effect="Rejected") for _ in range(3)]

    def test_eight_rounds_and_three_blocked_terminal_actions(self):
        io=FakeIO([*self.rounds,*self.blocked])
        report=exercise(self.initial,self.after_right,io)
        self.assertTrue(report["defeat_passed"])
        self.assertEqual(report["round_hashes"],list(ROUND_HASHES))
        self.assertEqual(report["scout_hp"],0)
        self.assertEqual([key for key,_ in io.keys],["x"]*9+["y","Return"])

    def test_red_transient_receipt_after_real_hit_is_allowed(self):
        rounds=self.rounds[:]
        rounds[2]=frame(3,effect="Rejected")
        io=FakeIO([*rounds,*self.blocked])
        self.assertTrue(exercise(self.initial,self.after_right,io)["defeat_passed"])

    def test_dropped_endturn_recovers_only_unchanged_prior_state(self):
        old=frame(0,effect="Rejected")
        io=FakeIO([old,*self.rounds,*self.blocked])
        report=exercise(self.initial,self.after_right,io)
        self.assertTrue(report["defeat_passed"])
        self.assertEqual(report["proof_files"][0],"action-defeat-round-1-retry.png")

    def test_two_dropped_endturn_inputs_rejected(self):
        old=frame(0,effect="Rejected")
        io=FakeIO([old,old])
        with self.assertRaisesRegex(ValueError,"checksum mismatch"):
            exercise(self.initial,self.after_right,io)

    def test_wrong_scout_hp_rejected_even_with_correct_hash(self):
        tampered=frame(1,scout_hp=22,effect="TurnEnded")
        io=FakeIO([tampered])
        with self.assertRaisesRegex(ValueError,"Scout depleted HP pixel mismatch"):
            exercise(self.initial,self.after_right,io)

    def test_wrong_raider_hp_rejected(self):
        tampered=frame(1,effect="TurnEnded")
        ImageDraw.Draw(tampered).rectangle((515,215,530,219),fill=(31,32,32))
        io=FakeIO([tampered])
        with self.assertRaisesRegex(ValueError,"Raider 20HP bar changed"):
            exercise(self.initial,self.after_right,io)

    def test_malformed_end_turn_effect_fails_closed(self):
        tampered=frame(1,effect="Selected")
        io=FakeIO([tampered])
        with self.assertRaisesRegex(ValueError,"receipt not Rejected"):
            exercise(self.initial,self.after_right,io)

    def test_defeated_scout_blue_body_must_disappear(self):
        fake=frame(8,scout_body=True)
        with self.assertRaisesRegex(ValueError,"defeated Scout blue pawn still visible"):
            _hp(fake,0)

    def test_defeat_hash_cannot_override_remaining_scout_hp(self):
        fake=frame(8,scout_hp=1,scout_body=False)
        with self.assertRaisesRegex(ValueError,"defeated Scout still has green HP"):
            _hp(fake,0)

    def test_terminal_endturn_must_not_create_round_nine(self):
        fake=frame(7,effect="Rejected")
        io=FakeIO([*self.rounds,fake,fake])
        with self.assertRaisesRegex(ValueError,"checksum mismatch"):
            exercise(self.initial,self.after_right,io)

    def test_post_defeat_attack_must_be_rejected(self):
        fake=frame(8,effect="Attacked")
        io=FakeIO([*self.rounds,self.blocked[0],fake])
        with self.assertRaisesRegex(ValueError,"receipt not Rejected"):
            exercise(self.initial,self.after_right,io)

    def test_post_defeat_confirm_must_be_rejected(self):
        fake=frame(8,effect="Selected")
        io=FakeIO([*self.rounds,*self.blocked[:2],fake])
        with self.assertRaisesRegex(ValueError,"receipt not Rejected"):
            exercise(self.initial,self.after_right,io)


if __name__ == "__main__":
    unittest.main()
