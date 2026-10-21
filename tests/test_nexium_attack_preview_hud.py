"""Stage54 synthetic/adversarial PNG cases for a real NeXium HUD auditor."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from PIL import ImageDraw
from test_nexium_attack_action import picture
from tools.nexium_attack_action import INITIAL_DUEL, ATTACKED_DUEL
from tools.nexium_duel_victory import ROUND4, VICTORY
from tools.nexium_attack_preview_hud import (
    _expect_forecast, _expect_hidden, _final_aim, verify_folder,
    GREEN, PURPLE, GOLD, DARK, HELP,
)


def screenshot(*, state=INITIAL_DUEL, selected=False, aiming=False,
               preview=False, lethal=False):
    im=picture(cursor=(520,276) if aiming else (480,256),
               state=state,selected=selected)
    draw=ImageDraw.Draw(im)
    draw.rectangle((0,660,1279,719),fill=HELP)
    if preview:
        draw.rectangle((141,676,324,697),fill=DARK)
        remains=0 if lethal else 123
        if remains:
            draw.rectangle((145,680,145+remains-1,693),fill=GREEN)
        draw.rectangle((145+remains,680,320,693),fill=PURPLE)
        if lethal:
            draw.rectangle((141,676,324,697),outline=GOLD)
    return im


class PreviewHudTests(unittest.TestCase):
    def test_normal_attack_shows_surviving_and_lost_hp(self):
        self.assertTrue(_expect_forecast(screenshot(selected=True,aiming=True,preview=True)))

    def test_lethal_attack_purple_full_width_and_gold_border(self):
        self.assertTrue(_expect_forecast(screenshot(state=ROUND4,selected=True,
                                                  aiming=True,preview=True,lethal=True),
                                         lethal=True))

    def test_unselected_and_already_attacked_hud_hidden(self):
        self.assertTrue(_expect_hidden(screenshot(selected=True)))
        self.assertTrue(_expect_hidden(screenshot(state=ATTACKED_DUEL,
                                                  selected=True,aiming=True)))

    def test_missing_forecast_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"HUD pixel mismatch"):
            _expect_forecast(screenshot(selected=True,aiming=True))

    def test_forged_purple_over_green_rejected(self):
        false=screenshot(selected=True,aiming=True,preview=True)
        ImageDraw.Draw(false).rectangle((160,686,160,686),fill=PURPLE)
        with self.assertRaisesRegex(ValueError,"left"):
            _expect_forecast(false)

    def test_wrong_damage_width_is_rejected(self):
        false=screenshot(selected=True,aiming=True,preview=True)
        ImageDraw.Draw(false).rectangle((280,686,280,686),fill=GREEN)
        with self.assertRaisesRegex(ValueError,"right"):
            _expect_forecast(false)

    def test_missing_lethal_outline_is_rejected(self):
        false=screenshot(state=ROUND4,selected=True,aiming=True,
                         preview=True,lethal=True)
        ImageDraw.Draw(false).point((141,686),fill=DARK)
        with self.assertRaisesRegex(ValueError,"border"):
            _expect_forecast(false,lethal=True)

    def test_illegal_residual_hud_after_strike_rejected(self):
        with self.assertRaisesRegex(ValueError,"failed to disappear"):
            _expect_hidden(screenshot(state=ATTACKED_DUEL,selected=True,
                                      aiming=True,preview=True))

    def test_aim_frame_gap_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            screenshot().save(p/"action-duel-aim-1.png")
            screenshot().save(p/"action-duel-aim-3.png")
            with self.assertRaisesRegex(ValueError,"incomplete"):
                _final_aim(p,"action-duel-aim-")

    def test_full_two_round_visual_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            screenshot().save(folder/"nexium-window.png")
            screenshot(selected=True).save(folder/"action-duel-selected.png")
            screenshot(selected=True,aiming=True,preview=True).save(
                folder/"action-duel-aim-1.png")
            screenshot(state=ATTACKED_DUEL,selected=True,aiming=True).save(
                folder/"action-duel-attacked.png")
            screenshot(state=ROUND4,selected=True,aiming=True,preview=True,
                       lethal=True).save(folder/"action-victory-round4-aim-nav-1.png")
            screenshot(state=VICTORY,selected=True,aiming=True).save(
                folder/"action-victory-round4-attacked.png")
            (folder/"attack-evidence.json").write_text(json.dumps({
                "attack_passed":True,"selected_proof":"action-duel-selected.png"
            }),encoding="utf8")
            (folder/"victory-evidence.json").write_text(json.dumps({
                "victory_passed":True
            }),encoding="utf8")
            self.assertTrue(verify_folder(folder,folder))

    def test_full_proof_rejects_false_game_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            screenshot(state=ROUND4).save(folder/"nexium-window.png")
            (folder/"attack-evidence.json").write_text(
                '{"attack_passed":true,"selected_proof":"action-duel-selected.png"}',
                encoding="utf8")
            for name in ("action-duel-selected.png","action-duel-aim-1.png",
                         "action-duel-attacked.png"):
                screenshot(selected=True,aiming=name!="action-duel-selected.png",
                           preview=name=="action-duel-aim-1.png").save(folder/name)
            (folder/"victory-evidence.json").write_text(
                '{"victory_passed":true}',encoding="utf8")
            screenshot(state=ROUND4,selected=True,aiming=True,
                       preview=True,lethal=True).save(
                folder/"action-victory-round4-aim-nav-1.png")
            screenshot(state=VICTORY,selected=True,aiming=True).save(
                folder/"action-victory-round4-attacked.png")
            with self.assertRaisesRegex(ValueError,"checksum mismatch"):
                verify_folder(folder,folder)


if __name__=="__main__":
    unittest.main()
