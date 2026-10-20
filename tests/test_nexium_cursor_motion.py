"""Synthetic-only tests of the two-screenshot cursor movement classifier."""
import unittest
from PIL import Image, ImageDraw
from tools.nexium_cursor_motion import yellow_center, evaluate_motion


def synthetic(cx=480, cy=256, *, cursor=True, legend=True):
    image = Image.new('RGB', (1280, 720), (14, 19, 32))
    draw = ImageDraw.Draw(image)
    if cursor:
        # Diamond-style yellow highlighted tile, as in our ROM-free renderer.
        for dy in range(-20, 21):
            reach = 2 * (20 - abs(dy))
            draw.line([(cx - reach, cy + dy), (cx + reach, cy + dy)], fill=(220, 178, 68))
    if legend:
        draw.rectangle((10, 670, 50, 700), fill=(220, 178, 68))
    return image


class CursorMotionTests(unittest.TestCase):
    def test_valid_right_movement(self):
        r = evaluate_motion(synthetic(), synthetic(520, 276))
        self.assertTrue(r['plausible_right_cursor_movement'])
        self.assertAlmostEqual(r['delta_x_pixels'], 40, delta=1)

    def test_no_movement_rejected(self):
        self.assertFalse(evaluate_motion(synthetic(), synthetic())['plausible_right_cursor_movement'])

    def test_left_movement_rejected(self):
        self.assertFalse(evaluate_motion(synthetic(), synthetic(440, 276))['plausible_right_cursor_movement'])

    def test_legend_only_rejected(self):
        self.assertIsNone(yellow_center(synthetic(cursor=False)))
        self.assertFalse(evaluate_motion(synthetic(cursor=False), synthetic(cursor=False))['plausible_right_cursor_movement'])

    def test_cursor_disappears(self):
        self.assertFalse(evaluate_motion(synthetic(), synthetic(cursor=False))['plausible_right_cursor_movement'])

    def test_wrong_size_raises(self):
        with self.assertRaises(ValueError):
            evaluate_motion(synthetic(), Image.new('RGB', (800, 500), 'black'))

    def test_tiny_frame_raises(self):
        with self.assertRaises(ValueError):
            yellow_center(Image.new('RGB', (40, 40), 'black'))


if __name__ == '__main__':
    unittest.main()
