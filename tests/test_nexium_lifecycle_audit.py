"""Synthetic tests for pre-close vs post-close panic classification."""
import unittest
from tools.nexium_lifecycle_audit import assess

LIFECYCLE = 'capture_done shutdown_requested\nwindowclose_sent\nemulator_exit_code=0\n'


class LifecycleAuditTests(unittest.TestCase):
    def test_clean_log_and_shutdown(self):
        self.assertTrue(assess('guest ready\n', 'guest ready\n', LIFECYCLE)['clean_lifecycle'])

    def test_panic_during_capture_is_not_assigned_to_shutdown(self):
        panic = 'thread main panicked at X11 window\n'
        r = assess('guest ready\n' + panic, 'guest ready\n' + panic, LIFECYCLE)
        self.assertIn('rust_panic', r['fatal_before_close'])
        self.assertEqual(r['fatal_after_close_request'], [])
        self.assertFalse(r['clean_lifecycle'])

    def test_post_close_panic_detected_not_suppressed(self):
        r = assess('guest ready\n', 'guest ready\nthread main panicked at X11\n', LIFECYCLE)
        self.assertIn('rust_panic', r['fatal_after_close_request'])
        self.assertFalse(r['clean_lifecycle'])

    def test_snapshot_mismatch_rejected(self):
        r = assess('not a prefix', 'guest ready\n', LIFECYCLE)
        self.assertFalse(r['snapshot_is_prefix_of_complete_log'])
        self.assertFalse(r['clean_lifecycle'])

    def test_forced_close_rejected_despite_zero_exit(self):
        r = assess('guest ready\n', 'guest ready\n', LIFECYCLE + 'forced_sigterm\n')
        self.assertFalse(r['normal_window_close_requested'])
        self.assertFalse(r['clean_lifecycle'])

    def test_x11_after_close_separately_reported(self):
        r = assess('guest ready\n', 'guest ready\nConnection(IoError(Custom))\n', LIFECYCLE)
        self.assertIn('x11_connection_failure', r['fatal_after_close_request'])

    def test_audio_warning_nonfatal(self):
        r = assess('ALSA lib error\n', 'ALSA lib error\n', LIFECYCLE)
        self.assertTrue(r['clean_lifecycle'])


if __name__ == '__main__':
    unittest.main()
