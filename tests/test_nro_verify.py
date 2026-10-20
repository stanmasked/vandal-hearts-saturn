"""Synthetic-only NRO format tests grounded in switch-tools elf2nro conventions."""
from pathlib import Path
import struct
import tempfile
import unittest

from tools.nro_verify import inspect_nro, HEADER_BYTES


def make_nro(*, text_size=0x1000, rodata_size=0x1000, data_size=0x1000,
             assets=b"", claimed_size=None):
    """Synthesize a plausible NRO: .text begins at file offset zero."""
    size = text_size + rodata_size + data_size
    body = bytearray(size)
    body[0x10:0x14] = b"NRO0"
    struct.pack_into("<I", body, 0x14, 0)
    struct.pack_into("<I", body, 0x18, claimed_size if claimed_size is not None else size)
    for index, pair in enumerate(((0, text_size), (text_size, rodata_size),
                                  (text_size + rodata_size, data_size))):
        struct.pack_into("<II", body, 0x20 + 8*index, *pair)
    return bytes(body) + assets


def aset_with_nacp(data=b"TEST"):
    header = bytearray(0x38)
    header[0:4] = b"ASET"
    struct.pack_into("<Q", header, 0x18, 0x38)
    struct.pack_into("<Q", header, 0x20, len(data))
    return bytes(header) + data


class NroTests(unittest.TestCase):
    def examine(self, content):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.nro"
            path.write_bytes(content)
            return inspect_nro(path)

    def test_realistic_text_offset_zero(self):
        result = self.examine(make_nro())
        self.assertEqual(result["format"], "NRO0")
        self.assertEqual(result["segments"]["text"]["offset"], 0)
        self.assertEqual(result["segments"]["text"]["bytes"], 0x1000)
        self.assertEqual(result["executable_bytes"], 0x3000)
        self.assertEqual(len(result["sha256"]), 64)

    def test_optional_embedded_nacp(self):
        result = self.examine(make_nro(assets=aset_with_nacp()))
        self.assertTrue(result["has_homebrew_assets"])

    def test_reject_elf_instead_of_nro(self):
        data = bytearray(make_nro())
        data[0x10:0x14] = b"ELF!"
        with self.assertRaisesRegex(ValueError, "NRO0"):
            self.examine(data)

    def test_invalid_claimed_executable_size(self):
        for size in (HEADER_BYTES - 1, 0x3000 + 200):
            with self.assertRaises(ValueError):
                self.examine(make_nro(claimed_size=size))

    def test_empty_text(self):
        with self.assertRaisesRegex(ValueError, "Empty"):
            self.examine(make_nro(text_size=0, rodata_size=0x1000, data_size=0))

    def test_text_too_short_to_contain_code(self):
        with self.assertRaisesRegex(ValueError, "start header"):
            self.examine(make_nro(text_size=HEADER_BYTES,
                                  rodata_size=0x1000, data_size=0))

    def test_text_segment_outside_executable(self):
        data = bytearray(make_nro())
        struct.pack_into("<I", data, 0x24, 0x4000)
        with self.assertRaisesRegex(ValueError, "outside"):
            self.examine(data)

    def test_rodata_overlaps_text(self):
        data = bytearray(make_nro())
        struct.pack_into("<I", data, 0x28, 0x800)
        with self.assertRaisesRegex(ValueError, "overlaps"):
            self.examine(data)

    def test_short_or_invalid_asset_header(self):
        for suffix in (b"ASET", b"junk", b"ASET" + bytes(4)):
            with self.assertRaisesRegex(ValueError, "ASET"):
                self.examine(make_nro(assets=suffix))

    def test_out_of_bounds_asset_section(self):
        header = bytearray(aset_with_nacp())
        struct.pack_into("<Q", header, 0x20, 999999)
        with self.assertRaisesRegex(ValueError, "nacp ASET"):
            self.examine(make_nro(assets=header))

    def test_reject_unsupported_asset_version(self):
        header = bytearray(aset_with_nacp())
        struct.pack_into("<I", header, 4, 1)
        with self.assertRaisesRegex(ValueError, "ASET version"):
            self.examine(make_nro(assets=header))

    def test_truncated_nro(self):
        with self.assertRaises(ValueError):
            self.examine(b"NRO0")


if __name__ == "__main__":
    unittest.main()
