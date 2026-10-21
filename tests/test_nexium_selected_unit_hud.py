"""Stage55 adversarial screenshot tests for REAL selected-ally HUD auditor."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from PIL import ImageDraw

from test_nexium_attack_action import picture
from tools.nexium_attack_action import INITIAL_DUEL,ATTACKED_DUEL
from tools.nexium_second_round import ROUND2
from tools.nexium_duel_victory import ROUND4,VICTORY
from tools.nexium_duel_defeat import ROUND_HASHES
from tools.nexium_selected_unit_hud import (
    expect_hidden, expect_visible, verify_folder,
    BLUE,DARK,HELP,READY,ACTED,NOT_MOVED,WHITE,DIGITS
)


def frame(state=INITIAL_DUEL, hp=22, *, selected=False,
          aimed=False, attacked=False, ghost=False):
    result=picture(cursor=(520,276) if aimed else (480,256),
                   state=state,selected=selected)
    draw=ImageDraw.Draw(result)
    draw.rectangle((0,660,1279,719),fill=HELP)
    if selected or ghost:
        draw.rectangle((350,668,993,711),fill=DARK)
        draw.rectangle((354,673,361,706),fill=BLUE)
        draw.rectangle((953,683,966,696),fill=ACTED if attacked else READY)
        draw.rectangle((976,683,987,696),fill=NOT_MOVED)
        # Four white uppercase stat label glyphs sampled by the real auditor.
        for x,y in ((501,684),(606,684),(725,684),(840,684)):
            draw.rectangle((x-1,y-1,x,y),fill=WHITE)
        # Synthetic HP digits: the same 3x5 pixel raster as SDL.
        for index,char in enumerate(str(hp)):
            for y,mask in enumerate(DIGITS[char]):
                for x in range(3):
                    if mask & (1 << (2-x)):
                        left=500+8*(3+index)+2*x
                        top=683+2*y
                        draw.rectangle((left,top,left+1,top+1),fill=WHITE)
    return result


def make_proof(folder):
    folder=Path(folder)
    outputs={
        "nexium-window.png":frame(),
        "action-duel-selected.png":frame(selected=True),
        "action-duel-attacked.png":frame(state=ATTACKED_DUEL,selected=True,
                                       aimed=True,attacked=True),
        "action-round2-ended.png":frame(state=ROUND2,aimed=True),
        "action-round2-selected.png":frame(state=ROUND2,selected=True,hp=19),
        "action-victory-round4-selected.png":frame(state=ROUND4,selected=True,hp=13),
        "action-victory-round4-attacked.png":frame(state=VICTORY,aimed=True),
        "action-defeat-round-8.png":frame(state=ROUND_HASHES[-1],aimed=True),
    }
    for name,image in outputs.items(): image.save(folder/name)
    for name,report in {
        "attack-evidence.json":{"attack_passed":True,
                                "selected_proof":"action-duel-selected.png"},
        "round2-evidence.json":{"selection_proof":"action-round2-selected.png",
                                "ended_proof":"action-round2-ended.png"},
        "victory-evidence.json":{"victory_passed":True,
                                 "round4_selection_proof":"action-victory-round4-selected.png"},
        "defeat-evidence.json":{"defeat_passed":True},
    }.items():
        (folder/name).write_text(json.dumps(report),encoding="utf-8")
    return folder


class SelectedUnitTests(unittest.TestCase):
    def test_initial_hidden_without_selection(self):
        self.assertTrue(expect_hidden(frame()))

    def test_selected_hud_shows_22_hp_and_unused_attack(self):
        self.assertTrue(expect_visible(frame(selected=True),22))

    def test_after_attack_remains_selected_but_action_used(self):
        self.assertTrue(expect_visible(frame(state=ATTACKED_DUEL,selected=True,
                                             aimed=True,attacked=True),22,attacked=True))

    def test_round_two_shows_exact_19_hp_digits(self):
        self.assertTrue(expect_visible(frame(state=ROUND2,selected=True,hp=19),19))

    def test_fourth_round_shows_exact_13_hp_digits(self):
        self.assertTrue(expect_visible(frame(state=ROUND4,selected=True,hp=13),13))

    def test_wrong_digits_with_correct_full_game_hash_fail(self):
        with self.assertRaisesRegex(ValueError,"HP digit mismatch"):
            expect_visible(frame(state=ROUND2,selected=True,hp=22),19)

    def test_missing_hp_label_is_rejected(self):
        fake=frame(selected=True)
        ImageDraw.Draw(fake).rectangle((500,683,501,684),fill=DARK)
        with self.assertRaisesRegex(ValueError,"hp_label"):
            expect_visible(fake,22)

    def test_wrong_attack_label_is_rejected(self):
        fake=frame(selected=True)
        ImageDraw.Draw(fake).rectangle((605,683,606,684),fill=DARK)
        with self.assertRaisesRegex(ValueError,"attack_label"):
            expect_visible(fake,22)

    def test_spent_action_cannot_be_forged_as_ready(self):
        with self.assertRaisesRegex(ValueError,"ready_or_acted"):
            expect_visible(frame(selected=True,attacked=False),22,attacked=True)

    def test_ghost_selection_after_victory_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"unit HUD pixel mismatch"):
            expect_hidden(frame(state=VICTORY,ghost=True))

    def test_ghost_selection_after_defeat_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"unit HUD pixel mismatch"):
            expect_hidden(frame(state=ROUND_HASHES[-1],ghost=True))

    def test_full_snapshot_sequence_correct(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=make_proof(tmp)
            self.assertTrue(verify_folder(folder,folder))

    def test_full_snapshot_sequence_wrong_round_four_hp_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=make_proof(tmp)
            frame(state=ROUND4,selected=True,hp=22).save(
                folder/"action-victory-round4-selected.png")
            with self.assertRaisesRegex(ValueError,"HP digit mismatch"):
                verify_folder(folder,folder)

    def test_full_snapshot_sequence_wrong_state_hash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=make_proof(tmp)
            frame(state=INITIAL_DUEL,selected=True,hp=19).save(
                folder/"action-round2-selected.png")
            with self.assertRaisesRegex(ValueError,"checksum mismatch"):
                verify_folder(folder,folder)

    def test_missing_round_two_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=make_proof(tmp)
            (folder/"action-round2-selected.png").unlink()
            with self.assertRaises((OSError,ValueError)):
                verify_folder(folder,folder)


if __name__=="__main__":
    unittest.main()
