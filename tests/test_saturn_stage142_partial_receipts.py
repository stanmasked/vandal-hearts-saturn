"""Stage142 invented-only receipt tests. Never consumes original Saturn media."""
from pathlib import Path
import tempfile
import unittest
from tools.saturn_stage142_partial_receipts import _expected, verify_receipt_pair


class ReceiptTests(unittest.TestCase):
    def make_pair(self, root, *, frame=24000):
        a,b = root/'control',root/'enabled'
        a.mkdir();b.mkdir()
        ev,st = _expected(frame)
        for path in (a,b):
            (path/'pad-events.txt').write_bytes(ev)
            (path/'pad-state.txt').write_bytes(st)
        return a,b

    def test_canonical_complete_prefix_passes_without_guest_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.make_pair(Path(tmp))
            r=verify_receipt_pair(a,b)
            self.assertTrue(r['canonical_host_pad_receipts_verified'])
            self.assertFalse(r['original_guest_input_consumption_verified'])
            self.assertFalse(r['tenth_c_effect_verified'])

    def test_empty_pad_buffers_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.make_pair(Path(tmp))
            for filename in ('pad-events.txt','pad-state.txt'):
                (a/filename).write_bytes(b'')
                with self.assertRaisesRegex(ValueError,'missing or unsafe'):
                    verify_receipt_pair(a,b)
                (a/filename).write_bytes((b/filename).read_bytes())

    def test_missing_press_or_release_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.make_pair(Path(tmp))
            p=a/'pad-events.txt'
            p.write_bytes(p.read_bytes().replace(b'VH_PAD frame=12246 button=C action=RELEASE\n',b''))
            with self.assertRaisesRegex(ValueError,'mismatch'):
                verify_receipt_pair(a,b)

    def test_state_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.make_pair(Path(tmp))
            p=a/'pad-state.txt'
            p.write_bytes(p.read_bytes().replace(b'frame=12240 button=C active_low_bit=0',
                                                   b'frame=12240 button=C active_low_bit=1'))
            with self.assertRaisesRegex(ValueError,'mismatch'):
                verify_receipt_pair(a,b)

    def test_extra_preinput_event_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.make_pair(Path(tmp))
            p=b/'pad-events.txt'
            p.write_bytes(p.read_bytes()+b'VH_PAD frame=12500 button=C action=PRESS\n')
            with self.assertRaisesRegex(ValueError,'mismatch'):
                verify_receipt_pair(a,b)

    def test_truncated_line_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.make_pair(Path(tmp))
            p=b/'pad-events.txt';p.write_bytes(p.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError,'incomplete'):
                verify_receipt_pair(a,b)

    def test_duplicate_event_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.make_pair(Path(tmp))
            p=b/'pad-events.txt';raw=p.read_bytes()
            p.write_bytes(raw+raw.splitlines()[0]+b'\n')
            with self.assertRaisesRegex(ValueError,'mismatch'):
                verify_receipt_pair(a,b)

    def test_invalid_window_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.make_pair(Path(tmp))
            for frame in (108000,12240,24001,120,0,-120):
                with self.subTest(frame=frame),self.assertRaises(ValueError):
                    verify_receipt_pair(a,b,through_frame=frame)

    def test_symlink_to_receipt_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.make_pair(Path(tmp))
            (b/'pad-events.txt').unlink()
            (b/'pad-events.txt').symlink_to(a/'pad-events.txt')
            with self.assertRaisesRegex(ValueError,'missing or unsafe'):
                verify_receipt_pair(a,b)

    def test_incorrect_initial_bit_witness_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.make_pair(Path(tmp))
            p=a/'pad-state.txt';p.write_bytes(p.read_bytes().replace(
                b'initial_start_bit=1',b'initial_start_bit=0'))
            with self.assertRaisesRegex(ValueError,'initial-bit'):
                verify_receipt_pair(a,b)

    def test_future_c_event_ignored_for_prefix_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.make_pair(Path(tmp))
            p=b/'pad-events.txt';p.write_bytes(p.read_bytes()+
                b'VH_PAD frame=108000 button=C action=PRESS\n')
            result=verify_receipt_pair(a,b)
            self.assertEqual(result['checked_through_frame'],24000)


if __name__=='__main__':unittest.main()
