"""Synthetic screenshot tests, no game captures or protected assets."""
import unittest
from PIL import Image, ImageDraw
from tools.nexium_frame_verify import color_components, verify_frame, _is_ally


def image_scene(*, legend=True, units=True, reverse=False, one_each=False):
    img = Image.new('RGB', (1280, 720), (14, 19, 32))
    draw = ImageDraw.Draw(img)
    if units:
        blue_xs = [440] if one_each else [440, 480]
        red_xs = [840] if one_each else [760, 840]
        if reverse:
            blue_xs, red_xs = red_xs, blue_xs
        for i, x in enumerate(blue_xs):
            draw.rectangle((x, 220 + i * 40, x + 23, 249 + i * 40), fill=(63, 167, 239))
        for i, x in enumerate(red_xs):
            draw.rectangle((x, 220 + i * 40, x + 23, 249 + i * 40), fill=(239, 79, 76))
    if legend:
        draw.rectangle((16, 677, 46, 698), fill=(63, 167, 239))
        draw.rectangle((55, 677, 85, 698), fill=(239, 79, 76))
    return img


class FrameVerifyTests(unittest.TestCase):
    def test_two_allies_two_enemies(self):
        verdict = verify_frame(image_scene())
        self.assertTrue(verdict['plausible_training_frame'])
        self.assertEqual(verdict['ally_components'], 2)
        self.assertEqual(verdict['enemy_components'], 2)

    def test_colored_legend_alone_not_a_success(self):
        self.assertFalse(verify_frame(image_scene(units=False))['plausible_training_frame'])

    def test_single_blue_and_red_rejected(self):
        self.assertFalse(verify_frame(image_scene(one_each=True))['plausible_training_frame'])

    def test_swapped_sides_rejected(self):
        self.assertFalse(verify_frame(image_scene(reverse=True))['plausible_training_frame'])

    def test_blank_frame_rejected(self):
        self.assertFalse(verify_frame(Image.new('RGB',(1280,720),'black'))['plausible_training_frame'])

    def test_small_frame_rejected(self):
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            verify_frame(Image.new('RGB',(320,200),'black'))

    def test_components_only_upper_game_region(self):
        img = image_scene(units=False)
        self.assertEqual(color_components(img, _is_ally), [])


if __name__ == '__main__':
    unittest.main()
