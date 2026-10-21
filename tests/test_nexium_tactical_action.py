"""Stage42 ROM-free screenshots: X11 input is accepted only with genuine pixel proof."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from PIL import Image, ImageDraw
from tools.nexium_tactical_action import (
    INITIAL, AFTER_SCOUT_MOVE, _selected_marker, exercise, verify_folder
)
from tools.nexium_visual_digest import (
    ANCHORS, ANCHOR_RGB, ANCHOR_SIZE, X, Y, PITCH, SIZE, ON_RGB, OFF_RGB
)


def picture(cursor, fingerprint=INITIAL, selected=False, selected_cursor=None):
    im = Image.new("RGB", (1280, 720), (14, 19, 32))
    d = ImageDraw.Draw(im)
    for bit in range(64):
        x = X + (bit % 8) * PITCH
        y = Y + (bit // 8) * PITCH
        rgb = ON_RGB if int(fingerprint, 16) & (1 << bit) else OFF_RGB
        d.rectangle((x, y, x + SIZE - 1, y + SIZE - 1), fill=rgb)
    for x, y in ANCHORS:
        d.rectangle((x, y, x + ANCHOR_SIZE - 1,
                     y + ANCHOR_SIZE - 1), fill=ANCHOR_RGB)
    x, y = cursor
    d.rectangle((x, y, x + 49, y + 22), fill=(220, 178, 68))
    if selected:
        # The selected unit can stay on its original tile while the cursor
        # previews an adjacent destination; these coordinates are independent.
        sx, sy = selected_cursor if selected_cursor is not None else cursor
        d.rectangle((sx + 10, sy - 35, sx + 42, sy + 5),
                    outline=(251, 220, 90), width=2)
    return im


class FakeIO:
    def __init__(self, answers):
        self.answers = list(answers)
        self.keys = []
        self.focused = False

    def capture_after(self, key, label):
        self.keys.append(key)
        if not self.answers:
            raise ValueError("unexpected duplicate input")
        return self.answers.pop(0)

    def focus(self):
        self.focused = True


class ActionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.start = picture((400, 250))
        self.right = picture((440, 270))
        self.back = picture((400, 250))
        self.selected = picture((400, 250), selected=True)
        self.aimed = picture((440, 270), selected=True, selected_cursor=(400, 250))
        self.moved = picture((440, 270), AFTER_SCOUT_MOVE)

    def test_marker_requires_genuine_selection_border(self):
        self.assertFalse(_selected_marker(self.back, (424.5, 261.0)))
        self.assertTrue(_selected_marker(self.selected, (424.5, 261.0)))

    def test_exact_one_tile_move_and_full_checksum(self):
        io = FakeIO([self.back, self.selected, self.aimed, self.moved])
        report = exercise(self.start, self.right, io)
        self.assertTrue(report["action_passed"])
        self.assertEqual(report["after_move_fingerprint"], AFTER_SCOUT_MOVE)
        self.assertEqual(io.keys, ["Left", "Return", "Right", "Return"])
        self.assertEqual(report["aimed_proof"], "action-aim-1.png")
        self.assertEqual(report["moved_proof"], "action-moved.png")
        self.assertFalse(io.focused)

    def test_two_tile_prior_right_restored_by_observation(self):
        io = FakeIO([self.right, self.back, self.selected,
                     self.aimed, self.moved])
        report = exercise(self.start, picture((480, 290)), io)
        self.assertTrue(report["action_passed"])
        self.assertEqual(io.keys.count("Left"), 2)

    def test_real_nexium_left_overshoot_corrected_by_right(self):
        io = FakeIO([picture((360, 230)), self.back, self.selected,
                     self.aimed, self.moved])
        report = exercise(self.start, self.right, io)
        self.assertTrue(report["action_passed"])
        self.assertEqual(io.keys, ["Left", "Right", "Return", "Right", "Return"])

    def test_repeated_two_tile_oscillation_fails_bounded(self):
        frames = [picture((360, 230)) if i % 2 == 0 else self.right
                  for i in range(8)]
        io = FakeIO(frames)
        with self.assertRaisesRegex(ValueError, "after 8 observations"):
            exercise(self.start, self.right, io)
        self.assertEqual(len(io.keys), 8)
        self.assertNotIn("Return", io.keys)

    def test_missed_aim_triggers_focus_and_retry(self):
        io = FakeIO([self.back, self.selected, self.back,
                     self.aimed, self.moved])
        report = exercise(self.start, self.right, io)
        self.assertTrue(report["action_passed"])
        self.assertTrue(io.focused)
        self.assertEqual(io.keys.count("Right"), 2)

    def test_aim_two_tile_overshoot_corrected_before_move(self):
        io = FakeIO([self.back, self.selected, picture((480, 290)),
                     self.aimed, self.moved])
        report = exercise(self.start, self.right, io)
        self.assertTrue(report["action_passed"])
        self.assertEqual(io.keys, ["Left", "Return", "Right", "Left", "Return"])

    def test_aim_two_tile_oscillation_is_bounded_no_commit(self):
        frames = [picture((480, 290)) if i % 2 == 0 else self.back
                  for i in range(8)]
        io = FakeIO([self.back, self.selected, *frames])
        with self.assertRaisesRegex(ValueError, "after 8 observations"):
            exercise(self.start, self.right, io)
        self.assertEqual(io.keys.count("Return"), 1)

    def test_wrong_row_rejected_without_commit(self):
        io = FakeIO([self.back, self.selected, picture((480, 390))])
        with self.assertRaisesRegex(ValueError, "left the Scout map row"):
            exercise(self.start, self.right, io)
        self.assertEqual(io.keys, ["Left", "Return", "Right"])

    def test_dropped_selection_fails_closed_before_aim(self):
        io = FakeIO([self.back, self.back, self.back])
        with self.assertRaisesRegex(ValueError, "selection outline not visible"):
            exercise(self.start, self.right, io)
        self.assertEqual(io.keys, ["Left", "Return", "space"])
        self.assertTrue(io.focused)

    def test_dropped_return_can_select_via_bounded_space_fallback(self):
        io = FakeIO([self.back, self.back, self.selected,
                     self.aimed, self.moved])
        report = exercise(self.start, self.right, io)
        self.assertTrue(report["action_passed"])
        self.assertEqual(report["selected_proof"], "action-selected-retry.png")
        self.assertEqual(io.keys, ["Left", "Return", "space", "Right", "Return"])

    def test_dropped_move_confirm_can_retry_if_state_unchanged(self):
        io = FakeIO([self.back, self.selected, self.aimed,
                     self.aimed, self.moved])
        report = exercise(self.start, self.right, io)
        self.assertTrue(report["action_passed"])
        self.assertEqual(report["moved_proof"], "action-moved-retry.png")
        self.assertEqual(io.keys, ["Left", "Return", "Right", "Return", "space"])

    def test_no_tactical_state_change_rejected_after_retry(self):
        io = FakeIO([self.back, self.selected, self.aimed,
                     self.aimed, self.aimed])
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            exercise(self.start, self.right, io)
        self.assertEqual(io.keys, ["Left", "Return", "Right", "Return", "space"])

    def test_wrong_fingerprint_prevents_repeated_commit(self):
        io = FakeIO([self.back, self.selected, self.aimed,
                     picture((440, 270), "0123456789abcdef")])
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            exercise(self.start, self.right, io)
        self.assertEqual(io.keys, ["Left", "Return", "Right", "Return"])

    def test_invalid_previous_state_rejected(self):
        io = FakeIO([])
        with self.assertRaises(ValueError):
            exercise(self.start, picture((440, 270), AFTER_SCOUT_MOVE), io)
        self.assertEqual(io.keys, [])

    def test_verify_folder_requires_actual_images(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "action-evidence.json").write_text(json.dumps({
                "action_passed": True,
                "initial_fingerprint": INITIAL,
                "after_move_fingerprint": AFTER_SCOUT_MOVE,
                "selected_proof": "action-selected.png",
                "aimed_proof": "action-aim-1.png",
                "moved_proof": "action-moved.png",
            }))
            with self.assertRaises(FileNotFoundError):
                verify_folder(folder)

    def test_verify_folder_rejects_forged_selection_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "nexium-window.png").write_bytes(b"")
            self.start.save(folder / "nexium-window.png")
            self.back.save(folder / "action-selected.png")
            self.aimed.save(folder / "action-aim-1.png")
            self.moved.save(folder / "action-moved.png")
            (folder / "action-evidence.json").write_text(json.dumps({
                "action_passed": True,
                "initial_fingerprint": INITIAL,
                "after_move_fingerprint": AFTER_SCOUT_MOVE,
                "selected_proof": "action-selected.png",
                "aimed_proof": "action-aim-1.png",
                "moved_proof": "action-moved.png",
            }))
            with self.assertRaisesRegex(ValueError, "selection not observed"):
                verify_folder(folder)


if __name__ == "__main__":
    unittest.main()
