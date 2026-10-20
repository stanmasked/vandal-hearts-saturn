"""Stage44 synthetic screenshot contract for the isolated ROM-free duel."""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
import unittest
from PIL import Image, ImageDraw
from tools.nexium_attack_action import (
    INITIAL_DUEL, ATTACKED_DUEL, _require_hp, exercise, verify_folder,
)
from tools.nexium_post_move import COLORS
from tools.nexium_visual_digest import (
    ANCHORS, ANCHOR_RGB, ANCHOR_SIZE, X, Y, PITCH, SIZE, ON_RGB, OFF_RGB,
)


def picture(cursor=(480, 256), state=INITIAL_DUEL, selected=False,
            hp=20, effect=None):
    im = Image.new("RGB", (1280,720), (14,19,32))
    draw = ImageDraw.Draw(im)
    for bit in range(64):
        x=X+(bit%8)*PITCH; y=Y+(bit//8)*PITCH
        value=ON_RGB if int(state,16)&(1<<bit) else OFF_RGB
        draw.rectangle((x,y,x+SIZE-1,y+SIZE-1),fill=value)
    for x,y in ANCHORS:
        draw.rectangle((x,y,x+ANCHOR_SIZE-1,y+ANCHOR_SIZE-1),fill=ANCHOR_RGB)
    # Stage44 Raider occupies (2,5), projected (520,276); HP bar y215..219.
    draw.rectangle((503,215,536,219),fill=(31,32,32))
    draw.rectangle((503,215,503+max(1,min(34,hp*34//26))-1,219),
                   fill=(117,221,109))
    x,y=cursor
    draw.rectangle((x,y,x+49,y+22),fill=(220,178,68))
    if selected:
        draw.rectangle((490,213,522,236),outline=(251,220,90),width=2)
    if effect is not None:
        draw.rectangle((1210,60,1225,75),fill=COLORS[effect])
    return im


class FakeIO:
    def __init__(self, frames):
        self.frames=list(frames)
        self.keys=[]
        self.focused=False

    def capture_after(self, key, label):
        self.keys.append((key,label))
        if not self.frames:
            raise ValueError("too many input keys")
        return self.frames.pop(0)

    def focus(self):
        self.focused=True


class DuelTests(unittest.TestCase):
    def setUp(self):
        self.initial=picture()
        self.after_right=picture(cursor=(520,276))
        self.returned=picture()
        self.selected=picture(selected=True)
        self.aimed=picture(cursor=(520,276), selected=True)
        self.attacked=picture(cursor=(520,276),selected=True,hp=14,
                              state=ATTACKED_DUEL,effect="Attacked")
        self.rejected=picture(cursor=(520,276),selected=True,hp=14,
                              state=ATTACKED_DUEL,effect="Rejected")

    def test_successful_attack_and_rejected_duplicate(self):
        io=FakeIO([self.returned,self.selected,self.aimed,
                   self.attacked,self.rejected])
        report=exercise(self.initial,self.after_right,io)
        self.assertTrue(report["attack_passed"])
        self.assertEqual(report["hp_after"],14)
        self.assertEqual([k for k,_ in io.keys],
                         ["Left","Return","Right","y","y"])

    def test_hp_bar_only_is_not_enough_without_digest(self):
        fake=picture(cursor=(520,276),selected=True,hp=14,
                     state=INITIAL_DUEL,effect="Attacked")
        io=FakeIO([self.returned,self.selected,self.aimed,fake])
        with self.assertRaisesRegex(ValueError,"checksum mismatch"):
            exercise(self.initial,self.after_right,io)

    def test_digest_only_is_not_enough_without_hp_loss(self):
        fake=picture(cursor=(520,276),selected=True,hp=20,
                     state=ATTACKED_DUEL,effect="Attacked")
        io=FakeIO([self.returned,self.selected,self.aimed,fake])
        with self.assertRaisesRegex(ValueError,"HP bar"):
            exercise(self.initial,self.after_right,io)

    def test_second_attack_cannot_change_battle(self):
        again=picture(cursor=(520,276),selected=True,hp=14,
                      state=ATTACKED_DUEL,effect="Attacked")
        io=FakeIO([self.returned,self.selected,self.aimed,
                   self.attacked,again])
        with self.assertRaisesRegex(ValueError,"receipt not Rejected"):
            exercise(self.initial,self.after_right,io)

    def test_selected_marker_needed_before_attack(self):
        io=FakeIO([self.returned,self.returned,self.returned])
        with self.assertRaisesRegex(ValueError,"Scout not visibly selected"):
            exercise(self.initial,self.after_right,io)
        self.assertNotIn("y",[k for k,_ in io.keys])

    def test_aim_overshoot_corrects_before_attack(self):
        overshot=picture(cursor=(560,296),selected=True)
        io=FakeIO([self.returned,self.selected,overshot,self.aimed,
                   self.attacked,self.rejected])
        result=exercise(self.initial,self.after_right,io)
        self.assertTrue(result["attack_passed"])
        self.assertEqual([k for k,_ in io.keys],
                         ["Left","Return","Right","Left","y","y"])

    def test_real_hp_pixel_delta(self):
        self.assertTrue(_require_hp(self.initial,"full"))
        self.assertTrue(_require_hp(self.attacked,"damaged"))
        with self.assertRaisesRegex(ValueError,"HP bar"):
            _require_hp(self.initial,"damaged")

    def test_folder_verification_rejects_tampered_final_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            self.initial.save(folder/"nexium-window.png")
            self.selected.save(folder/"action-duel-selected.png")
            self.attacked.save(folder/"action-duel-attacked.png")
            self.rejected.save(folder/"action-duel-rejected.png")
            (folder/"attack-evidence.json").write_text(json.dumps({
                "attack_passed":True, "initial_fingerprint":INITIAL_DUEL,
                "attacked_fingerprint":ATTACKED_DUEL, "hp_before":20,
                "hp_after":14, "second_attack_rejected":True,
                "selected_proof":"action-duel-selected.png",
                "attack_proof":"action-duel-attacked.png",
                "reject_proof":"action-duel-rejected.png",
            }))
            self.assertTrue(verify_folder(folder))
            self.attacked.save(folder/"action-duel-rejected.png")
            with self.assertRaisesRegex(ValueError,"receipt not Rejected"):
                verify_folder(folder)


if __name__ == "__main__":
    unittest.main()
