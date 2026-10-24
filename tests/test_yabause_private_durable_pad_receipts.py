"""Invented-only tests for Stage143 source transformer; no original Yabause file."""
from pathlib import Path
import unittest

from tools.patch_yabause_private_durable_pad_receipts import (
    MODE_START, MODE_END, PAD_OPEN, STATE_OPEN,
    instrument_durable_pad_receipts_on_stage125,
)


def fixture():
    body = [PAD_OPEN, '         fprintf(vh107_pad_log, "START\\n");\n', STATE_OPEN,
            '         fprintf(vh109_state_log, "INITIAL\\n");\n']
    for _ in range(10):
        body.append('         PerPadCPressed(vh107_pad);\n')
        body.append('         fprintf(vh107_pad_log, "C PRESS\\n");\n')
        body.append('         fprintf(vh109_state_log, "C DOWN\\n");\n')
        body.append('         PerPadCReleased(vh107_pad);\n')
        body.append('         fprintf(vh107_pad_log, "C RELEASE\\n");\n')
        body.append('         fprintf(vh109_state_log, "C UP\\n");\n')
    return '#include <stdio.h>\nOUTSIDE_PREFIX\n' + MODE_START + ''.join(body) + MODE_END + '\nOUTSIDE_SUFFIX\n'


class DurablePadReceiptPatchTests(unittest.TestCase):
    def test_adds_two_unbuffered_streams_before_any_write(self):
        source = fixture()
        result = instrument_durable_pad_receipts_on_stage125(source.encode()).decode()
        self.assertEqual(result.count('setvbuf(vh107_pad_log, NULL, _IONBF, 0)'), 1)
        self.assertEqual(result.count('setvbuf(vh109_state_log, NULL, _IONBF, 0)'), 1)
        self.assertLess(result.index('fopen(vh107_pad_log_path'), result.index('setvbuf(vh107_pad_log'))
        self.assertLess(result.index('setvbuf(vh107_pad_log'), result.index('fprintf(vh107_pad_log,'))
        self.assertLess(result.index('fopen(vh109_state_path'), result.index('setvbuf(vh109_state_log'))
        self.assertLess(result.index('setvbuf(vh109_state_log'), result.index('fprintf(vh109_state_log,'))

    def test_source_outside_private_mode_unchanged(self):
        source = fixture()
        result = instrument_durable_pad_receipts_on_stage125(source.encode()).decode()
        self.assertTrue(result.startswith('#include <stdio.h>\nOUTSIDE_PREFIX\n'))
        self.assertTrue(result.endswith('\nOUTSIDE_SUFFIX\n'))

    def test_missing_pad_open_anchor_fails_closed(self):
        source = fixture().replace(PAD_OPEN, '', 1)
        with self.assertRaisesRegex(ValueError, 'open anchors'):
            instrument_durable_pad_receipts_on_stage125(source.encode())

    def test_duplicate_state_open_anchor_fails_closed(self):
        source = fixture().replace(STATE_OPEN, STATE_OPEN + STATE_OPEN, 1)
        with self.assertRaisesRegex(ValueError, 'open anchors'):
            instrument_durable_pad_receipts_on_stage125(source.encode())

    def test_double_application_fails_closed(self):
        first = instrument_durable_pad_receipts_on_stage125(fixture().encode())
        with self.assertRaisesRegex(ValueError, 'already applied'):
            instrument_durable_pad_receipts_on_stage125(first)

    def test_wrong_tenth_c_count_fails_closed(self):
        source = fixture().replace('PerPadCPressed(vh107_pad);\n', '', 1)
        with self.assertRaisesRegex(ValueError, 'event count'):
            instrument_durable_pad_receipts_on_stage125(source.encode())

    def test_unbuffered_setup_failure_codes_are_unique(self):
        source = fixture()
        result = instrument_durable_pad_receipts_on_stage125(source.encode()).decode()
        self.assertEqual(result.count('return 385;'), 1)
        self.assertEqual(result.count('return 386;'), 1)


if __name__ == '__main__':
    unittest.main()
