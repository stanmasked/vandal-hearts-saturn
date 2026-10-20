"""Synthetic PNG regressions for Stage43's guest-observable no-repeat/cancel."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from PIL import Image, ImageDraw
from tools.nexium_post_move import exercise, verify_folder, _effect, COLORS
from tools.nexium_tactical_action import INITIAL, AFTER_SCOUT_MOVE
from tools.nexium_visual_digest import (
    ANCHORS, ANCHOR_RGB, ANCHOR_SIZE, X, Y, PITCH, SIZE, ON_RGB, OFF_RGB
)


def picture(cursor, fingerprint=INITIAL, selected_tile=None, effect=None):
    im = Image.new("RGB", (1280, 720), (14, 19, 32))
    draw = ImageDraw.Draw(im)
    for bit in range(64):
        x = X + (bit % 8) * PITCH
        y = Y + (bit // 8) * PITCH
        value = ON_RGB if int(fingerprint, 16) & (1 << bit) else OFF_RGB
        draw.rectangle((x, y, x + SIZE - 1, y + SIZE - 1), fill=value)
    for x, y in ANCHORS:
        draw.rectangle((x, y, x + ANCHOR_SIZE - 1,
                        y + ANCHOR_SIZE - 1), fill=ANCHOR_RGB)
    if selected_tile is not None:
        x, y = selected_tile
        draw.rectangle((x + 10, y - 50, x + 42, y - 27),
                       outline=(251, 220, 90), width=2)
    x, y = cursor
    draw.rectangle((x, y, x + 49, y + 22), fill=(220, 178, 68))
    if effect is not None:
        draw.rectangle((1210, 60, 1225, 75), fill=COLORS[effect])
    return im


class FakeIO:
    def __init__(self, frames):
        self.frames = list(frames)
        self.keys = []

    def capture_after(self, key, label):
        self.keys.append((key, label))
        if not self.frames:
            raise ValueError("unexpected guest action")
        return self.frames.pop(0)


class PostMoveTests(unittest.TestCase):
    def setUp(self):
        self.initial = picture((400, 250))
        self.moved = picture((440, 270), AFTER_SCOUT_MOVE,
                             selected_tile=(440, 270), effect="Moved")
        self.returned = picture((400, 250), AFTER_SCOUT_MOVE,
                                selected_tile=(440, 270))
        self.rejected = picture((400, 250), AFTER_SCOUT_MOVE,
                                selected_tile=(440, 270), effect="Rejected")
        self.cancelled = picture((400, 250), AFTER_SCOUT_MOVE,
                                 effect="Cancelled")

    def test_success_requires_both_guest_action_receipts(self):
        io = FakeIO([self.returned, self.rejected, self.cancelled])
        result = exercise(self.initial, self.moved, io)
        self.assertTrue(result["second_move_rejected"])
        self.assertTrue(result["selection_cancelled"])
        self.assertEqual([key for key, _ in io.keys],
                         ["Left", "Return", "BackSpace"])

    def test_reject_without_receipt_is_not_a_pass(self):
        io = FakeIO([self.returned, self.returned])
        with self.assertRaisesRegex(ValueError, "receipt not Rejected"):
            exercise(self.initial, self.moved, io)
        self.assertNotIn("BackSpace", [key for key, _ in io.keys])

    def test_cancel_command_without_receipt_is_not_a_pass(self):
        io = FakeIO([self.returned, self.rejected, self.returned])
        with self.assertRaisesRegex(ValueError, "receipt not Cancelled"):
            exercise(self.initial, self.moved, io)

    def test_cancel_must_remove_actual_selection(self):
        still_selected = picture((400, 250), AFTER_SCOUT_MOVE,
                                 selected_tile=(440, 270), effect="Cancelled")
        io = FakeIO([self.returned, self.rejected, still_selected])
        with self.assertRaisesRegex(ValueError, "outline remained"):
            exercise(self.initial, self.moved, io)

    def test_wrong_state_rejected_before_action(self):
        io = FakeIO([])
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            exercise(self.initial, self.initial, io)

    def test_return_overshoot_recovers_bounded(self):
        overshot = picture((360, 230), AFTER_SCOUT_MOVE,
                           selected_tile=(440, 270))
        io = FakeIO([overshot, self.returned, self.rejected, self.cancelled])
        result = exercise(self.initial, self.moved, io)
        self.assertTrue(result["post_passed"])
        self.assertEqual([key for key, _ in io.keys],
                         ["Left", "Right", "Return", "BackSpace"])

    def test_return_two_cell_oscillation_fails_without_confirm(self):
        frames = [picture((360, 230), AFTER_SCOUT_MOVE,
                          selected_tile=(440, 270)) if i % 2 == 0 else
                  self.moved for i in range(8)]
        io = FakeIO(frames)
        with self.assertRaisesRegex(ValueError, "not observed"):
            exercise(self.initial, self.moved, io)
        self.assertEqual(len(io.keys), 8)
        self.assertNotIn("Return", [key for key, _ in io.keys])

    def test_receipt_color_validation(self):
        self.assertTrue(_effect(self.moved, "Moved"))
        self.assertTrue(_effect(self.rejected, "Rejected"))
        self.assertTrue(_effect(self.cancelled, "Cancelled"))
        with self.assertRaisesRegex(ValueError, "not Rejected"):
            _effect(self.cancelled, "Rejected")

    def test_verify_folder_reads_real_pngs(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.initial.save(folder / "nexium-window.png")
            self.moved.save(folder / "action-moved.png")
            self.rejected.save(folder / "action-post-rejected.png")
            self.cancelled.save(folder / "action-post-cancelled.png")
            (folder / "post-move-evidence.json").write_text(json.dumps({
                "post_passed": True,
                "moved_fingerprint": AFTER_SCOUT_MOVE,
                "second_move_rejected": True,
                "selection_cancelled": True,
                "rejected_proof": "action-post-rejected.png",
                "cancelled_proof": "action-post-cancelled.png",
            }))
            self.assertTrue(verify_folder(folder))
            self.moved.save(folder / "action-post-cancelled.png")
            with self.assertRaises(ValueError):
                verify_folder(folder)


if __name__ == "__main__":
    unittest.main()
