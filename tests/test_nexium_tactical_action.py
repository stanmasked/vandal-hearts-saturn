"""Synthetic frames using production yellow-cursor and visual-checksum decoders."""
from __future__ import annotations
import tempfile
from pathlib import Path
import unittest

from PIL import Image, ImageDraw
from tools.nexium_tactical_action import INITIAL, AFTER_SCOUT_MOVE, exercise, verify_folder
from tools.nexium_visual_digest import ANCHORS, ANCHOR_RGB, ANCHOR_SIZE, X, Y, PITCH, SIZE, ON_RGB, OFF_RGB


def picture(cursor, fingerprint=INITIAL):
    im=Image.new("RGB",(1280,720),(14,19,32))
    d=ImageDraw.Draw(im)
    for bit in range(64):
        x=X+bit%8*PITCH; y=Y+bit//8*PITCH
        rgb=ON_RGB if int(fingerprint,16)&(1<<bit) else OFF_RGB
        d.rectangle((x,y,x+SIZE-1,y+SIZE-1),fill=rgb)
    for x,y in ANCHORS:
        d.rectangle((x,y,x+ANCHOR_SIZE-1,y+ANCHOR_SIZE-1),fill=ANCHOR_RGB)
    x,y=cursor
    d.rectangle((x,y,x+49,y+22),fill=(220,178,68))
    return im


class FakeIO:
    def __init__(self, answers):
        self.answers=list(answers)
        self.keys=[]
        self.focused=False
    def capture_after(self, key, label):
        self.keys.append(key)
        if not self.answers:
            raise ValueError("unexpected duplicate input")
        return self.answers.pop(0)
    def focus(self):
        self.focused=True


class ActionEvidenceTests(unittest.TestCase):
    def test_exact_one_tile_move_and_full_checksum(self):
        io=FakeIO([picture((400,250)), picture((400,250)),
                   picture((440,270)), picture((440,270),AFTER_SCOUT_MOVE)])
        report=exercise(picture((400,250)),picture((440,270)),io)
        self.assertTrue(report["action_passed"])
        self.assertEqual(report["after_move_fingerprint"],AFTER_SCOUT_MOVE)
        self.assertEqual(io.keys,["Left","Return","Right","Return"])
        self.assertFalse(io.focused)

    def test_two_tile_prior_right_restored_by_observation(self):
        io=FakeIO([picture((440,270)),picture((400,250)),picture((400,250)),
                   picture((440,270)),picture((440,270),AFTER_SCOUT_MOVE)])
        report=exercise(picture((400,250)),picture((480,290)),io)
        self.assertTrue(report["action_passed"])
        self.assertEqual(io.keys.count("Left"),2)

    def test_missed_aim_triggers_one_focus_retry(self):
        io=FakeIO([picture((400,250)),picture((400,250)),
                   picture((400,250)),picture((440,270)),
                   picture((440,270),AFTER_SCOUT_MOVE)])
        report=exercise(picture((400,250)),picture((440,270)),io)
        self.assertTrue(report["action_passed"])
        self.assertTrue(io.focused)
        self.assertEqual(io.keys.count("Right"),2)

    def test_wrong_tile_rejected_without_commit(self):
        io=FakeIO([picture((400,250)),picture((400,250)),picture((480,290))])
        with self.assertRaisesRegex(ValueError,"exactly one tile"):
            exercise(picture((400,250)),picture((440,270)),io)
        self.assertEqual(io.keys,["Left","Return","Right"])

    def test_no_tactical_state_change_rejected(self):
        io=FakeIO([picture((400,250)),picture((400,250)),
                   picture((440,270)),picture((440,270),INITIAL)])
        with self.assertRaisesRegex(ValueError,"checksum mismatch"):
            exercise(picture((400,250)),picture((440,270)),io)

    def test_invalid_previous_state_rejected(self):
        io=FakeIO([])
        with self.assertRaises(ValueError):
            exercise(picture((400,250)),picture((440,270),AFTER_SCOUT_MOVE),io)
        self.assertEqual(io.keys,[])

    def test_verify_folder_requires_actual_images(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            (folder/"action-evidence.json").write_text('{"action_passed":true,"initial_fingerprint":"'+INITIAL+'","after_move_fingerprint":"'+AFTER_SCOUT_MOVE+'"}')
            with self.assertRaises(FileNotFoundError):
                verify_folder(folder)


if __name__ == "__main__":
    unittest.main()
