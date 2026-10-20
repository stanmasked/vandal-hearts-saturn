"""Synthetic-only tests for verifying the state checksum visible in NeXium."""
import unittest
from PIL import Image, ImageDraw
from tools.nexium_visual_digest import (
    decode, ANCHORS, ANCHOR_RGB, INITIAL_TRAINING_FINGERPRINT, OFF_RGB, ON_RGB
)


def synthetic(fingerprint=INITIAL_TRAINING_FINGERPRINT, anchors=True):
    im = Image.new("RGB", (1280, 720), (14, 19, 32))
    d = ImageDraw.Draw(im)
    for bit in range(64):
        x, y = 20 + bit % 8 * 12, 20 + bit // 8 * 12
        c = ON_RGB if (int(fingerprint, 16) >> bit) & 1 else OFF_RGB
        d.rectangle((x, y, x + 7, y + 7), fill=c)
    if anchors:
        for x, y in ANCHORS:
            d.rectangle((x, y, x + 7, y + 7), fill=ANCHOR_RGB)
    return im


class VisualStateTests(unittest.TestCase):
    def test_authentic_training_hash(self):
        r = decode(synthetic())
        self.assertTrue(r["matches_expected_training_state"])
        self.assertEqual(r["decoded_fingerprint"], INITIAL_TRAINING_FINGERPRINT)
        self.assertEqual(r["anchors_found"], 3)
        self.assertEqual(r["unrecognized_cells"], 0)

    def test_one_flip_fails(self):
        different = f"{int(INITIAL_TRAINING_FINGERPRINT,16)^1:016x}"
        r = decode(synthetic(different))
        self.assertFalse(r["matches_expected_training_state"])
        self.assertEqual(r["decoded_fingerprint"], different)

    def test_missing_anchors_fails(self):
        r = decode(synthetic(anchors=False))
        self.assertFalse(r["matches_expected_training_state"])
        self.assertEqual(r["anchors_found"], 0)

    def test_blank_screen_fails(self):
        r = decode(Image.new("RGB", (1280, 720), "black"))
        self.assertFalse(r["matches_expected_training_state"])
        self.assertEqual(r["unrecognized_cells"], 64)

    def test_corrupted_cell_cannot_decode(self):
        image = synthetic()
        image.putpixel((24, 24), (255, 255, 255))
        r = decode(image)
        self.assertIsNone(r["decoded_fingerprint"])
        self.assertEqual(r["unrecognized_cells"], 1)

    def test_small_color_error_tolerated(self):
        image = synthetic()
        image.putpixel((24, 24), (61, 211, 125) if int(INITIAL_TRAINING_FINGERPRINT,16)&1 else (43, 58, 71))
        self.assertTrue(decode(image)["matches_expected_training_state"])

    def test_wrong_resolution_rejected(self):
        with self.assertRaises(ValueError):
            decode(Image.new("RGB", (800, 450)))

    def test_malformed_reference_rejected(self):
        with self.assertRaises(ValueError):
            decode(synthetic(), "too-short")
        with self.assertRaises(ValueError):
            decode(synthetic(), "z" * 16)

    def test_non_initial_reference_supported(self):
        image = synthetic("0123456789abcdef")
        self.assertTrue(decode(image, "0123456789abcdef")["matches_expected_training_state"])


if __name__ == "__main__":
    unittest.main()
