"""Pure synthetic unit tests of header inspection; no games or Switch SDK."""
from pathlib import Path
import struct
import tempfile
import unittest

from tools.nro_verify import inspect_nro, HEADER_BYTES


def make_nro(*, text_bytes=32, trailing=b"", claimed_size=None):
    body = bytearray(HEADER_BYTES + 32)
    body[0x10:0x14] = b"NRO0"
    struct.pack_into("<I", body, 0x14, 1)
    struct.pack_into("<I", body, 0x18,
                     claimed_size if claimed_size is not None else len(body))
    struct.pack_into("<II", body, 0x20, HEADER_BYTES, text_bytes)
    return bytes(body) + trailing


class NroTests(unittest.TestCase):
    def examine(self, content):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.nro"
            path.write_bytes(content)
            return inspect_nro(path)

    def test_valid_executable(self):
        result = self.examine(make_nro())
        self.assertEqual(result["format"], "NRO0")
        self.assertFalse(result["has_homebrew_assets"])
        self.assertEqual(result["segments"]["text"]["bytes"], 32)
        self.assertEqual(len(result["sha256"]), 64)

    def test_assets(self):
        result = self.examine(make_nro(trailing=b"ASET" + bytes(64)))
        self.assertTrue(result["has_homebrew_assets"])

    def test_invalid_magic(self):
        data = bytearray(make_nro())
        data[0x10:0x14] = b"ELF!"
        with self.assertRaisesRegex(ValueError, "NRO0"):
            self.examine(data)

    def test_invalid_claimed_length(self):
        for n in (HEADER_BYTES - 1, HEADER_BYTES + 200):
            with self.assertRaises(ValueError):
                self.examine(make_nro(claimed_size=n))

    def test_empty_code(self):
        with self.assertRaisesRegex(ValueError, "Empty"):
            self.examine(make_nro(text_bytes=0))

    def test_code_outside_image(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            self.examine(make_nro(text_bytes=1024))

    def test_unknown_trailing_data(self):
        with self.assertRaisesRegex(ValueError, "ASET"):
            self.examine(make_nro(trailing=b"junk"))

    def test_too_short(self):
        with self.assertRaises(ValueError):
            self.examine(b"NRO0")


if __name__ == "__main__":
    unittest.main()
