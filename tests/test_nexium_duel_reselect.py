"""Stage45 synthetic negatives for the real-guest duel continuation."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from test_nexium_attack_action import picture, FakeIO
from tools.nexium_attack_action import INITIAL_DUEL, ATTACKED_DUEL
from tools.nexium_duel_reselect import exercise, verify_folder


class DuelReselectTests(unittest.TestCase):
    def setUp(self):
        self.initial = picture()
        self.prior = picture(cursor=(520,276),selected=True,hp=14,
                             state=ATTACKED_DUEL,effect="Rejected")
        self.cancelled = picture(cursor=(520,276),selected=False,hp=14,
                                 state=ATTACKED_DUEL,effect="Cancelled")
        self.returned = picture(cursor=(480,256),hp=14,state=ATTACKED_DUEL)
        self.reselected = picture(cursor=(480,256),selected=True,hp=14,
                                  state=ATTACKED_DUEL,effect="Selected")
        self.aimed = picture(cursor=(520,276),selected=True,hp=14,
                             state=ATTACKED_DUEL)
        self.rejected = picture(cursor=(520,276),selected=True,hp=14,
                                state=ATTACKED_DUEL,effect="Rejected")

    def test_full_cancel_reselect_attack_reject(self):
        io=FakeIO([self.cancelled,self.returned,self.reselected,
                   self.aimed,self.rejected])
        receipt=exercise(self.initial,self.prior,io)
        self.assertTrue(receipt["reselect_passed"])
        self.assertEqual([key for key,_ in io.keys],
                         ["BackSpace","Left","Return","Right","y"])
        self.assertFalse(io.focused)

    def test_dropped_arrows_detected_and_refocused(self):
        frames=[self.cancelled,*([self.cancelled]*5),
                self.returned,self.reselected,self.aimed,self.rejected]
        io=FakeIO(frames)
        receipt=exercise(self.initial,self.prior,io)
        self.assertTrue(receipt["reselect_passed"])
        self.assertTrue(io.focused)
        self.assertEqual(len([x for x in receipt["steps"] if x.get("stalled")]),5)

    def test_twelve_missed_arrows_fail_closed(self):
        io=FakeIO([self.cancelled,*([self.cancelled]*12)])
        with self.assertRaisesRegex(ValueError,"within twelve observations"):
            exercise(self.initial,self.prior,io)
        self.assertEqual(len(io.keys),13)
        self.assertNotIn("Return",[key for key,_ in io.keys])

    def test_dropped_cancel_rejected(self):
        io=FakeIO([self.prior])
        with self.assertRaisesRegex(ValueError,"receipt not Cancelled"):
            exercise(self.initial,self.prior,io)
        self.assertEqual(len(io.keys),1)

    def test_cancel_receipt_but_outline_present_rejected(self):
        still_selected=picture(cursor=(520,276),selected=True,hp=14,
                               state=ATTACKED_DUEL,effect="Cancelled")
        io=FakeIO([still_selected])
        with self.assertRaisesRegex(ValueError,"outline not cleared"):
            exercise(self.initial,self.prior,io)

    def test_reselect_must_show_outline_after_retry(self):
        io=FakeIO([self.cancelled,self.returned,self.returned,self.returned])
        with self.assertRaisesRegex(ValueError,"never appeared"):
            exercise(self.initial,self.prior,io)
        self.assertNotIn("y",[key for key,_ in io.keys])

    def test_reattack_cannot_damage_raider_again(self):
        dishonest=picture(cursor=(520,276),selected=True,hp=8,
                          state=ATTACKED_DUEL,effect="Rejected")
        io=FakeIO([self.cancelled,self.returned,self.reselected,
                   self.aimed,dishonest])
        with self.assertRaisesRegex(ValueError,"HP bar"):
            exercise(self.initial,self.prior,io)

    def test_reattack_needs_red_reject_receipt(self):
        fake=picture(cursor=(520,276),selected=True,hp=14,
                     state=ATTACKED_DUEL,effect="Attacked")
        io=FakeIO([self.cancelled,self.returned,self.reselected,
                   self.aimed,fake])
        with self.assertRaisesRegex(ValueError,"receipt not Rejected"):
            exercise(self.initial,self.prior,io)

    def test_folder_verifier_reads_png_not_only_json(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)
            self.initial.save(f/"nexium-window.png")
            picture(cursor=(480,256),selected=True,hp=20,
                    state=INITIAL_DUEL).save(f/"action-duel-selected.png")
            picture(cursor=(520,276),selected=True,hp=14,
                    state=ATTACKED_DUEL,effect="Attacked").save(f/"action-duel-attacked.png")
            self.prior.save(f/"action-duel-rejected.png")
            self.cancelled.save(f/"action-reselect-cancelled.png")
            self.reselected.save(f/"action-reselect-selected.png")
            self.rejected.save(f/"action-reselect-rejected.png")
            (f/"attack-evidence.json").write_text(json.dumps({
                "attack_passed":True,"initial_fingerprint":INITIAL_DUEL,
                "attacked_fingerprint":ATTACKED_DUEL,"hp_before":20,
                "hp_after":14,"second_attack_rejected":True,
                "selected_proof":"action-duel-selected.png",
                "attack_proof":"action-duel-attacked.png",
                "reject_proof":"action-duel-rejected.png",
            }))
            (f/"reselect-evidence.json").write_text(json.dumps({
                "reselect_passed":True,"attacked_fingerprint":ATTACKED_DUEL,
                "hp_after":14,"repeat_attack_after_reselect_rejected":True,
                "cancelled_proof":"action-reselect-cancelled.png",
                "selected_proof":"action-reselect-selected.png",
                "rejected_proof":"action-reselect-rejected.png",
            }))
            self.assertTrue(verify_folder(f))
            self.cancelled.save(f/"action-reselect-rejected.png")
            with self.assertRaisesRegex(ValueError,"receipt not Rejected"):
                verify_folder(f)


if __name__ == "__main__":
    unittest.main()
