"""ROM-free checksum registration under emulator scaling and HUD obstruction."""
import unittest
from PIL import Image, ImageDraw
from tools.nexium_visual_digest import (
    ANCHORS, ANCHOR_RGB, ANCHOR_SIZE, INITIAL_TRAINING_FINGERPRINT,
    OFF_RGB, ON_RGB, decode, X, Y, PITCH, SIZE,
)


def synthetic(fingerprint=INITIAL_TRAINING_FINGERPRINT, anchors=True):
    im = Image.new('RGB', (1280, 720), (14, 19, 32))
    draw = ImageDraw.Draw(im)
    number = int(fingerprint, 16)
    for i in range(64):
        x, y = X + i % 8 * PITCH, Y + i // 8 * PITCH
        rgb = ON_RGB if (number >> i) & 1 else OFF_RGB
        draw.rectangle((x, y, x + SIZE - 1, y + SIZE - 1), fill=rgb)
    if anchors:
        for x, y in ANCHORS:
            draw.rectangle((x, y, x + ANCHOR_SIZE - 1, y + ANCHOR_SIZE - 1), fill=ANCHOR_RGB)
    return im


def obstruct_left_hud(im):
    im = im.copy()
    ImageDraw.Draw(im).rectangle((10, 5, 242, 157), fill=(0, 0, 0))
    return im


class VisualDigestRegistrationTests(unittest.TestCase):
    def test_native_training_fingerprint(self):
        result = decode(synthetic())
        self.assertTrue(result['matches_expected_training_state'], result)
        self.assertEqual(result['decoded_fingerprint'], INITIAL_TRAINING_FINGERPRINT)
        self.assertEqual(result['anchors_found'], 3)

    def test_hud_overlay_preserves_top_right_marker(self):
        result = decode(obstruct_left_hud(synthetic()))
        self.assertTrue(result['matches_expected_training_state'], result)

    def test_real_neXium_window_dimensions_with_scaling(self):
        original = obstruct_left_hud(synthetic())
        resized = original.resize((1279, 700), Image.Resampling.BILINEAR)
        result = decode(resized)
        self.assertTrue(result['matches_expected_training_state'], result)
        self.assertLess(result['scale_y'], 1)

    def test_shifted_capture_with_letterbox(self):
        full = synthetic().resize((1260, 680), Image.Resampling.BILINEAR)
        window = Image.new('RGB', (1279, 700), (1, 1, 1))
        window.paste(full, (9, 11))
        self.assertTrue(decode(window)['matches_expected_training_state'])

    def test_wrong_bit_rejected(self):
        wrong = f'{int(INITIAL_TRAINING_FINGERPRINT,16)^1:016x}'
        result = decode(synthetic(wrong))
        self.assertEqual(result['decoded_fingerprint'], wrong)
        self.assertFalse(result['matches_expected_training_state'])

    def test_missing_anchors_rejected(self):
        result = decode(synthetic(anchors=False))
        self.assertFalse(result['matches_expected_training_state'])
        self.assertEqual(result['anchors_found'], 0)

    def test_blank_rejected(self):
        result = decode(Image.new('RGB', (1279, 700), 'black'))
        self.assertIsNone(result['decoded_fingerprint'])
        self.assertFalse(result['matches_expected_training_state'])

    def test_corrupt_one_pixel_rejected(self):
        image = synthetic()
        image.putpixel((X + SIZE//2, Y + SIZE//2), (255, 255, 255))
        result = decode(image)
        self.assertEqual(result['unrecognized_cells'], 1)
        self.assertFalse(result['matches_expected_training_state'])

    def test_small_color_noise_tolerated(self):
        image = synthetic()
        color = ON_RGB if int(INITIAL_TRAINING_FINGERPRINT,16)&1 else OFF_RGB
        image.putpixel((X+SIZE//2, Y+SIZE//2), tuple(v-3 for v in color))
        self.assertTrue(decode(image)['matches_expected_training_state'])

    def test_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            decode(Image.new('RGB', (80, 80)))

    def test_malformed_reference(self):
        with self.assertRaises(ValueError):
            decode(synthetic(), 'not-hex')

    def test_another_known_fingerprint(self):
        self.assertTrue(decode(synthetic('0123456789abcdef'), '0123456789abcdef')['matches_expected_training_state'])

    def test_false_magenta_noise_fails_closed(self):
        image = synthetic()
        ImageDraw.Draw(image).rectangle((1245, 80, 1254, 89), fill=ANCHOR_RGB)
        self.assertFalse(decode(image)['matches_expected_training_state'])


if __name__ == '__main__':
    unittest.main()
