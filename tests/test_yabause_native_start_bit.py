"""Stage109 ROM-free test for genuine historical C68K pad-bit instrumentation."""
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from tools.patch_yabause_native_start_bit import (
    PRESS_BIT, CONNECT_EXTRA, PRESS_EXTRA, RELEASE_EXTRA, FINALIZE_EXTRA,
    instrument_native_start_bit,
)
from tools.saturn_private_start_ab import CONTROL, START, FRAME_COUNT
from tools.saturn_private_start_bit_ab import (
    CONTROL_STATE, PRESSED_STATE, audit_native_padbit_ab,
)


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data +
            struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def _png() -> bytes:
    lines = (b"\x00" + b"\x13\x21\x34" * 64) * 64
    return (b"\x89PNG\r\n\x1a\n" +
            _chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0)) +
            _chunk(b"IDAT", zlib.compress(lines)) +
            _chunk(b"IEND", b""))


class SaturnStartBitSourceTests(unittest.TestCase):
    def test_actual_upstream_active_low_bit_not_a_fake_button(self):
        self.assertEqual(PRESS_BIT, 0x08)
        self.assertIn("vh107_pad->padbits[0] & 0x08U", CONNECT_EXTRA)
        self.assertIn("vh107_pad->padbits[0] & 0x08U", PRESS_EXTRA)
        self.assertIn("vh107_pad->padbits[0] & 0x08U", RELEASE_EXTRA)
        self.assertIn("VH_PADSTATE initial_start_bit=1", CONNECT_EXTRA)
        self.assertIn("VH_PADSTATE frame=%d start_bit=0", PRESS_EXTRA)
        self.assertIn("VH_PADSTATE frame=%d start_bit=1", RELEASE_EXTRA)
        self.assertIn("VH_PADSTATE mode=%d completed_frames=%d", FINALIZE_EXTRA)
        self.assertIn("fclose(vh109_state_log)", FINALIZE_EXTRA)

    def test_invalid_or_tampered_yabause_sources_fail_closed(self):
        for data in (b"", b"garbage", b"int main() { return 0; }"):
            with self.subTest(len=len(data)), self.assertRaises(ValueError):
                instrument_native_start_bit(data)


class SaturnStartBitPrivateABTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        root = Path(t.name)
        root.chmod(0o700)
        self.control = root / "control"
        self.pressed = root / "pressed"
        for folder, events, bitlog in (
            (self.control, CONTROL, CONTROL_STATE),
            (self.pressed, START, PRESSED_STATE),
        ):
            folder.mkdir(mode=0o700)
            self._write(folder, "pad-events.txt", events)
            self._write(folder, "pad-state.txt", bitlog)
            self._write(folder, "fad.vhcdlog", b"VHCD_FAD 150\n")
            self._write(folder, f"frame-{FRAME_COUNT}.png", _png())

    @staticmethod
    def _write(folder, name, raw):
        path = folder / name
        path.write_bytes(raw)
        path.chmod(0o600)

    def check(self):
        return audit_native_padbit_ab(self.control, self.pressed)

    def test_two_fake_receipts_verify_native_host_bit_only(self):
        result = self.check()
        self.assertTrue(result["no_input_pad_start_bit_stayed_released"])
        self.assertTrue(result["start_press_seen_in_host_padbits_as_active_low_zero"])
        self.assertTrue(result["start_release_seen_in_host_padbits_as_high_one"])
        self.assertFalse(result["actual_guest_smpc_read_verified"])
        self.assertFalse(result["actual_game_menu_transition_verified"])
        self.assertFalse(result["actual_first_battle_verified"])
        self.assertNotIn(str(self.control), str(result))
        self.assertNotIn(str(self.pressed), str(result))

    def test_inverted_or_wrong_release_bits_fail(self):
        path = self.pressed / "pad-state.txt"
        for data in (
            PRESSED_STATE.replace(b"start_bit=0", b"start_bit=1"),
            PRESSED_STATE.replace(b"frame=12066", b"frame=12065"),
            PRESSED_STATE.replace(b"initial_start_bit=1", b"initial_start_bit=0"),
            PRESSED_STATE + b"EXTRA DATA\n",
        ):
            with self.subTest(state=data):
                self._write(self.pressed, path.name, data)
                with self.assertRaises(ValueError):
                    self.check()
        self._write(self.pressed, path.name, PRESSED_STATE)

    def test_control_cannot_falsely_press_start(self):
        self._write(self.control, "pad-state.txt", PRESSED_STATE)
        with self.assertRaises(ValueError):
            self.check()

    def test_receipt_file_permissions_and_symlink_rejected(self):
        path = self.pressed / "pad-state.txt"
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            self.check()
        path.chmod(0o600)
        backup = self.pressed / "backup-state.txt"
        path.rename(backup)
        path.symlink_to(backup)
        with self.assertRaises((ValueError, OSError)):
            self.check()

    def test_mismatching_stage107_event_receipt_fails(self):
        self._write(self.pressed, "pad-events.txt",
                    START.replace(b"frame=12060", b"frame=12000"))
        with self.assertRaises(ValueError):
            self.check()


if __name__ == "__main__":
    unittest.main()
