"""Stage50 synthetic PNG acceptance/negative cases for full homebrew victory.

These test the genuine image-decoding functions, not just claimed JSON state.
Actual guest completion must still pass the independent NeXium CI route.
"""
from __future__ import annotations

import unittest
from PIL import ImageDraw

from test_nexium_attack_action import FakeIO
from test_nexium_second_round import frame as earlier_frame
from tools.nexium_second_round import ROUND2_ATTACK
from tools.nexium_duel_victory import (
    ROUND3, ROUND3_ATTACK, ROUND4, VICTORY, _hp, exercise,
)


def frame(state, scout_hp, raider_hp, *, cursor=(520,276),
          selected=False, effect=None):
    image = earlier_frame(cursor=cursor, state=state, scout_hp=scout_hp,
                          raider_hp=raider_hp, selected=selected, effect=effect)
    if raider_hp == 0:
        # A dead Raider has no sprite and no HP bar in actual SDL. The
        # upstream synthetic picture helper draws 1 green pixel even at 0.
        ImageDraw.Draw(image).rectangle((503,215,536,219),fill=(31,32,32))
    return image


class VictoryTests(unittest.TestCase):
    def setUp(self):
        self.initial = frame("9376e23745926630", 22, 20,
                             cursor=(480,256))
        self.prior = frame(ROUND2_ATTACK, 19, 8, selected=True,
                           effect="Rejected")
        self.end3 = frame(ROUND3, 16, 8, effect="Rejected")
        self.scout3 = frame(ROUND3, 16, 8, cursor=(480,256))
        self.selected3 = frame(ROUND3, 16, 8, cursor=(480,256),
                               selected=True, effect="Selected")
        self.aim3 = frame(ROUND3, 16, 8, selected=True)
        self.hit3 = frame(ROUND3_ATTACK, 16, 2, selected=True,
                          effect="Attacked")
        self.reject3 = frame(ROUND3_ATTACK, 16, 2, selected=True,
                             effect="Rejected")
        self.end4 = frame(ROUND4, 13, 2, effect="TurnEnded")
        self.scout4 = frame(ROUND4, 13, 2, cursor=(480,256))
        self.selected4 = frame(ROUND4, 13, 2, cursor=(480,256),
                               selected=True, effect="Selected")
        self.aim4 = frame(ROUND4, 13, 2, selected=True)
        self.hit4 = frame(VICTORY, 13, 0, selected=True,
                          effect="Attacked")
        self.reject_turn = frame(VICTORY, 13, 0, selected=True,
                                  effect="Rejected")
        self.reject_hit = frame(VICTORY, 13, 0, selected=True,
                                 effect="Rejected")

    def frames(self):
        return [
            self.end3, self.scout3, self.selected3, self.aim3,
            self.hit3, self.reject3, self.end4, self.scout4,
            self.selected4, self.aim4, self.hit4,
            self.reject_turn, self.reject_hit,
        ]

    def test_complete_victory_requires_all_real_image_checkpoints(self):
        io = FakeIO(self.frames())
        result = exercise(self.initial, self.prior, io)
        self.assertTrue(result["victory_passed"])
        self.assertEqual(result["victory_hash"], VICTORY)
        self.assertTrue(result["terminal_turn_and_attack_rejected"])
        self.assertEqual([key for key,_ in io.keys], [
            "x", "Left", "Return", "Right", "y", "y",
            "x", "Left", "Return", "Right", "y", "x", "y",
        ])

    def test_two_missed_end_turn_x_inputs_fail_closed(self):
        io = FakeIO([self.prior, self.prior])
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            exercise(self.initial, self.prior, io)
        self.assertEqual([key for key,_ in io.keys], ["x", "x"])

    def test_end_turn_wrong_scout_hp_rejected(self):
        wrong = frame(ROUND3, 19, 8, effect="TurnEnded")
        io = FakeIO([wrong])
        with self.assertRaisesRegex(ValueError, "registered HP pixel mismatch"):
            exercise(self.initial, self.prior, io)

    def test_end_turn_unknown_receipt_rejected(self):
        wrong = frame(ROUND3, 16, 8, effect="Selected")
        io = FakeIO([wrong])
        with self.assertRaisesRegex(ValueError, "receipt not Rejected"):
            exercise(self.initial, self.prior, io)

    def test_drop_scout_selection_prevents_attack(self):
        not_selected = frame(ROUND3, 16, 8, cursor=(480,256),
                             effect="Selected")
        io = FakeIO([self.end3, self.scout3, not_selected, not_selected])
        with self.assertRaisesRegex(ValueError, "Scout not visually selected"):
            exercise(self.initial, self.prior, io)
        self.assertNotIn("y", [key for key,_ in io.keys])

    def test_unchanged_raider_hp_prevents_round3_claim(self):
        false_hit = frame(ROUND3_ATTACK, 16, 8, selected=True,
                          effect="Attacked")
        io = FakeIO([self.end3, self.scout3, self.selected3,
                     self.aim3, false_hit])
        with self.assertRaisesRegex(ValueError, "registered HP pixel mismatch"):
            exercise(self.initial, self.prior, io)

    def test_killed_raider_must_have_no_green_hp_bar(self):
        forged = earlier_frame(cursor=(520,276), state=VICTORY,
                               scout_hp=13, raider_hp=0, selected=True,
                               effect="Attacked")
        with self.assertRaisesRegex(ValueError, "registered HP pixel mismatch"):
            _hp(forged, 13, 0)

    def test_victory_hash_but_raider_sprite_present_rejected(self):
        forged = self.hit4.copy()
        ImageDraw.Draw(forged).rectangle((518,245,522,247),fill=(239,79,76))
        with self.assertRaisesRegex(ValueError, "defeated Raider still"):
            _hp(forged, 13, 0)

    def test_false_victory_digest_rejected(self):
        fake = frame(ROUND4, 13, 0, selected=True, effect="Attacked")
        io = FakeIO(self.frames()[:10] + [fake])
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            exercise(self.initial, self.prior, io)

    def test_repeated_end_turn_cannot_advance_victory(self):
        wrong = frame(ROUND4, 13, 0, selected=True, effect="Rejected")
        io = FakeIO(self.frames()[:11] + [wrong])
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            exercise(self.initial, self.prior, io)

    def test_post_victory_attack_must_show_rejected_receipt(self):
        wrong = frame(VICTORY, 13, 0, selected=True, effect="Attacked")
        io = FakeIO(self.frames()[:-1] + [wrong])
        with self.assertRaisesRegex(ValueError, "receipt not Rejected"):
            exercise(self.initial, self.prior, io)


if __name__ == "__main__":
    unittest.main()
