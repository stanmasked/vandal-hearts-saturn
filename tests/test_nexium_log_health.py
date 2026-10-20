"""Synthetic-only tests for NeXium host-log health classification."""
import tempfile
from pathlib import Path
import unittest
from tools.nexium_log_health import assess_log, inspect_log, MAX_LOG_BYTES


class NexiumLogHealthTests(unittest.TestCase):
    def test_ordinary_alsa_warnings_are_nonfatal(self):
        log = 'ALSA lib pcm.c:2722: [error.pcm] Unknown PCM default\nFPS: 57.2\n'
        result = assess_log(log)
        self.assertTrue(result['no_known_fatal_host_errors'])
        self.assertTrue(result['audio_device_warning_present'])

    def test_rust_panic_is_fatal(self):
        result = assess_log("thread 'main' panicked at winit/src/window.rs:1")
        self.assertIn('rust_panic', result['fatal_categories'])
        self.assertFalse(result['no_known_fatal_host_errors'])

    def test_x11_connection_failure_is_fatal(self):
        result = assess_log('Connection(IoError(Custom { kind: Other }))')
        self.assertIn('x11_connection_failure', result['fatal_categories'])

    def test_vulkan_lost_or_segmentation_fault(self):
        for message in ('VK_ERROR_DEVICE_LOST', 'Segmentation fault (core dumped)'):
            self.assertFalse(assess_log(message)['no_known_fatal_host_errors'])

    def test_empty_log_not_stability_proof(self):
        result = assess_log(' \n')
        self.assertFalse(result['no_known_fatal_host_errors'])
        self.assertFalse(result['log_nonempty'])

    def test_reject_oversize_log(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'big.log'
            with path.open('wb') as f:
                f.truncate(MAX_LOG_BYTES + 1)
            with self.assertRaises(ValueError):
                inspect_log(path)

    def test_no_full_host_stacktrace_exported(self):
        secret = '/home/runner/sensitive/internal/panic/location.rs'
        result = assess_log('panicked at ' + secret)
        self.assertNotIn(secret, str(result))
        self.assertEqual(result['fatal_categories'], ['rust_panic'])


if __name__ == '__main__':
    unittest.main()
