"""Mocked orchestration tests; stage34 real frame checked separately."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image
from tools.nexium_guest_evidence import EXPECTED_INPUT_RECEIPT, examine_pair, inspect_files


def state(ok=True, value='ae38b0b5ab887f00'):
    return {'matches_expected_training_state': ok, 'decoded_fingerprint': value}


def motion(ok=True):
    return {'plausible_right_cursor_movement': ok,
            'delta_x_pixels': 72.0 if ok else 0.0,
            'delta_y_pixels': 34.5 if ok else 0.0}


class GuestEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.first = Image.new('RGB', (1280, 720), 'black')
        self.second = Image.new('RGB', (1280, 720), 'black')

    def run_case(self, initial=None, after=None, movement=None, receipt=EXPECTED_INPUT_RECEIPT):
        with patch('tools.nexium_guest_evidence.decode', side_effect=[initial or state(), after or state()]):
            with patch('tools.nexium_guest_evidence.evaluate_motion', return_value=movement or motion()):
                return examine_pair(self.first, self.second, receipt)

    def test_good_two_frame_input_and_state(self):
        result = self.run_case()
        self.assertTrue(result['guest_visual_evidence_passed'])
        self.assertEqual(result['before_fingerprint'], result['after_fingerprint'])
        self.assertFalse(result['host_exit_status_verified'])

    def test_no_input_receipt_cannot_pass(self):
        result = self.run_case(receipt='')
        self.assertFalse(result['guest_visual_evidence_passed'])

    def test_no_cursor_displacement_cannot_pass(self):
        result = self.run_case(movement=motion(False))
        self.assertFalse(result['guest_visual_evidence_passed'])

    def test_initial_wrong_hash_cannot_pass(self):
        result = self.run_case(initial=state(False, 'bad0000000000000'))
        self.assertFalse(result['guest_visual_evidence_passed'])

    def test_after_wrong_hash_cannot_pass(self):
        result = self.run_case(after=state(False, 'bad0000000000000'))
        self.assertFalse(result['guest_visual_evidence_passed'])

    def test_invalid_receipt_not_treated_as_success(self):
        result = self.run_case(receipt='input_attempted=Right dispatch=failed')
        self.assertFalse(result['guest_visual_evidence_passed'])

    def test_missing_screenshot_is_explicit_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(FileNotFoundError):
                inspect_files(root/'missing.png', root/'missing-after.png', root/'missing.txt')


if __name__ == '__main__':
    unittest.main()
