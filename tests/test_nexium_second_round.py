"""Stage48 synthetic PNG tests: real end-round, counterattack and next hit."""
import json
import tempfile
import unittest
from pathlib import Path
from PIL import ImageDraw

from test_nexium_attack_action import FakeIO, picture
from tools.nexium_attack_action import ATTACKED_DUEL, INITIAL_DUEL
from tools.nexium_second_round import ROUND2, ROUND2_ATTACK, _hp, exercise, verify_folder


def frame(cursor=(520,276),state=ROUND2,scout_hp=19,raider_hp=14,
          selected=False,effect=None):
    image=picture(cursor=cursor,state=state,selected=selected,
                  hp=raider_hp,effect=effect)
    draw=ImageDraw.Draw(image)
    draw.rectangle((463,195,496,199),fill=(31,32,32))
    width=max(1,min(34,scout_hp*34//26))
    draw.rectangle((463,195,463+width-1,199),fill=(117,221,109))
    return image


class RoundTwoTests(unittest.TestCase):
    def setUp(self):
        self.initial=frame(cursor=(480,256),state=INITIAL_DUEL,
                           scout_hp=22,raider_hp=20)
        self.prior=frame(state=ATTACKED_DUEL,scout_hp=22,raider_hp=14,
                         selected=True,effect="Rejected")
        self.ended=frame(effect="TurnEnded")
        self.unselected=frame(effect="Rejected")
        self.returned=frame(cursor=(480,256))
        self.selected=frame(cursor=(480,256),selected=True,effect="Selected")
        self.aimed=frame(selected=True)
        self.attacked=frame(state=ROUND2_ATTACK,scout_hp=19,raider_hp=8,
                            selected=True,effect="Attacked")
        self.rejected=frame(state=ROUND2_ATTACK,scout_hp=19,raider_hp=8,
                            selected=True,effect="Rejected")

    def frames(self):
        return [self.ended,self.unselected,self.returned,self.selected,
                self.aimed,self.attacked,self.rejected]

    def test_live_sequence_all_six_transitions(self):
        io=FakeIO(self.frames())
        report=exercise(self.initial,self.prior,io)
        self.assertTrue(report["second_round_passed"])
        self.assertEqual(report["round2_fingerprint"],ROUND2)
        self.assertEqual(report["round2_attack_fingerprint"],ROUND2_ATTACK)
        self.assertEqual([k for k,_ in io.keys],
                         ["x","y","Left","Return","Right","y","y"])

    def test_end_turn_key_without_state_transition_retries_only_once(self):
        before=frame(state=ATTACKED_DUEL,scout_hp=22,raider_hp=14,
                     selected=True,effect="Rejected")
        io=FakeIO([before,*self.frames()])
        report=exercise(self.initial,self.prior,io)
        self.assertTrue(report["second_round_passed"])
        self.assertTrue(io.focused)
        self.assertEqual([k for k,_ in io.keys][:2],["x","x"])
        self.assertEqual(report["ended_proof"],"action-round2-ended-retry.png")

    def test_missed_both_end_turn_inputs_fail_closed(self):
        io=FakeIO([self.prior,self.prior])
        with self.assertRaisesRegex(ValueError,"checksum mismatch"):
            exercise(self.initial,self.prior,io)
        self.assertEqual([k for k,_ in io.keys],["x","x"])

    def test_enemy_did_not_hurt_scout_rejected(self):
        fake=frame(state=ROUND2,scout_hp=22,raider_hp=14,effect="TurnEnded")
        io=FakeIO([fake])
        with self.assertRaisesRegex(ValueError,"HP pixel mismatch for scout_lost"):
            exercise(self.initial,self.prior,io)

    def test_forged_turn_ended_receipt_does_not_count(self):
        fake=frame(state=ROUND2,scout_hp=19,raider_hp=14,effect="Rejected")
        io=FakeIO([fake])
        with self.assertRaisesRegex(ValueError,"receipt not TurnEnded"):
            exercise(self.initial,self.prior,io)

    def test_new_round_cannot_attack_without_selection(self):
        fake=frame(state=ROUND2_ATTACK,scout_hp=19,raider_hp=8,
                   selected=False,effect="Attacked")
        io=FakeIO([self.ended,fake])
        with self.assertRaisesRegex(ValueError,"checksum mismatch"):
            exercise(self.initial,self.prior,io)

    def test_scout_selection_must_reappear(self):
        still_unselected=frame(cursor=(480,256),effect="Selected")
        io=FakeIO([self.ended,self.unselected,self.returned,
                   still_unselected,still_unselected])
        with self.assertRaisesRegex(ValueError,"outline missing"):
            exercise(self.initial,self.prior,io)

    def test_round_two_hp_bar_requires_actual_second_hit(self):
        fake=frame(state=ROUND2_ATTACK,scout_hp=19,raider_hp=14,
                   selected=True,effect="Attacked")
        io=FakeIO([self.ended,self.unselected,self.returned,self.selected,
                   self.aimed,fake])
        with self.assertRaisesRegex(ValueError,"HP pixel mismatch for raider_lost"):
            exercise(self.initial,self.prior,io)

    def test_repeat_attack_must_be_explicitly_rejected(self):
        fake=frame(state=ROUND2_ATTACK,scout_hp=19,raider_hp=8,
                   selected=True,effect="Attacked")
        io=FakeIO([self.ended,self.unselected,self.returned,self.selected,
                   self.aimed,self.attacked,fake])
        with self.assertRaisesRegex(ValueError,"receipt not Rejected"):
            exercise(self.initial,self.prior,io)

    def test_second_round_image_checker_reopens_all_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            self.initial.save(p/"nexium-window.png")
            frame(cursor=(480,256),state=INITIAL_DUEL,
                  scout_hp=22,raider_hp=20,selected=True).save(p/"action-duel-selected.png")
            frame(state=ATTACKED_DUEL,scout_hp=22,raider_hp=14,
                  selected=True,effect="Attacked").save(p/"action-duel-attacked.png")
            self.prior.save(p/"action-duel-rejected.png")
            frame(state=ATTACKED_DUEL,scout_hp=22,raider_hp=14,
                  effect="Cancelled").save(p/"action-reselect-cancelled.png")
            frame(cursor=(480,256),state=ATTACKED_DUEL,
                  scout_hp=22,raider_hp=14,selected=True,
                  effect="Selected").save(p/"action-reselect-selected.png")
            self.prior.save(p/"action-reselect-rejected.png")
            self.ended.save(p/"action-round2-ended.png")
            self.unselected.save(p/"action-round2-no-select.png")
            self.selected.save(p/"action-round2-selected.png")
            self.attacked.save(p/"action-round2-attacked.png")
            self.rejected.save(p/"action-round2-rejected.png")
            (p/"attack-evidence.json").write_text(json.dumps({
                "attack_passed":True,"initial_fingerprint":INITIAL_DUEL,
                "attacked_fingerprint":ATTACKED_DUEL,
                "hp_before":20,"hp_after":14,
                "second_attack_rejected":True,
                "selected_proof":"action-duel-selected.png",
                "attack_proof":"action-duel-attacked.png",
                "reject_proof":"action-duel-rejected.png"}))
            (p/"reselect-evidence.json").write_text(json.dumps({
                "reselect_passed":True,"attacked_fingerprint":ATTACKED_DUEL,
                "hp_after":14,"repeat_attack_after_reselect_rejected":True,
                "cancelled_proof":"action-reselect-cancelled.png",
                "selected_proof":"action-reselect-selected.png",
                "rejected_proof":"action-reselect-rejected.png"}))
            (p/"round2-evidence.json").write_text(json.dumps({
                "format":"VHS48-ROM-free-second-round-v1",
                "second_round_passed":True,
                "round2_fingerprint":ROUND2,
                "round2_attack_fingerprint":ROUND2_ATTACK,
                "scout_hp_before":22,"scout_hp_after":19,
                "raider_hp_before":14,"raider_hp_after":8,
                "second_round_repeated_attack_rejected":True,
                "ended_proof":"action-round2-ended.png",
                "no_selection_proof":"action-round2-no-select.png",
                "selection_proof":"action-round2-selected.png",
                "attack_proof":"action-round2-attacked.png",
                "rejection_proof":"action-round2-rejected.png"}))
            self.assertTrue(verify_folder(p))
            self.attacked.save(p/"action-round2-rejected.png")
            with self.assertRaisesRegex(ValueError,"receipt not Rejected"):
                verify_folder(p)


if __name__=="__main__":
    unittest.main()
