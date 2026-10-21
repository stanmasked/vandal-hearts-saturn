"""ROM-free tests for Sega Saturn RAW MODE1/2352 ISO9660 metadata reader."""
import tempfile
import unittest
from pathlib import Path

from tools.saturn_iso import SaturnISO, both32


def both(n):
    return n.to_bytes(4, "little") + n.to_bytes(4, "big")


def record(name, extent, length, directory=False):
    name = name if isinstance(name, bytes) else name.encode("ascii")
    size = 33 + len(name) + (len(name) % 2 == 0)
    value = bytearray(size)
    value[0] = size
    value[2:10] = both(extent)
    value[10:18] = both(length)
    value[25] = 2 if directory else 0
    value[32] = len(name)
    value[33:33 + len(name)] = name
    return value


def create_image(path, *, bad_sync=False, outside=False):
    sectors = [bytearray(2048) for _ in range(22)]
    sectors[0][:16] = b"SEGA SEGASATURN "
    sectors[0][40:47] = b"T-9526G"
    sectors[16][:7] = b"\x01CD001\x01"
    sectors[16][40:53] = b"VANDAL_HEARTS"
    sectors[16][80:88] = both(22)
    sectors[16][156:190] = record(b"\x00", 20, 2048, directory=True)
    contents = (record(b"\x00", 20, 2048, directory=True) +
                record(b"\x01", 20, 2048, directory=True) +
                record("MAP_1_1C.BIN;1", 500 if outside else 21, 100))
    sectors[20][:len(contents)] = contents
    with path.open("wb") as stream:
        for i, sector in enumerate(sectors):
            sync = bytes(12) if bad_sync and i == 16 else bytes.fromhex("00ffffffffffffffffffff00")
            raw = sync + bytes((0, 2, i % 60, 1)) + sector + bytes(288)
            stream.write(raw)


class SaturnISOTest(unittest.TestCase):
    def test_valid_synthetic_disc(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "synthetic.bin"
            create_image(image)
            report = SaturnISO(image).inspect(include_files=True)
            self.assertEqual(report["boot_product_code"], "T-9526G")
            self.assertEqual(report["volume_id"], "VANDAL_HEARTS")
            self.assertEqual(report["files"], 1)
            self.assertEqual(report["extension_counts"], {"BIN": 1})
            self.assertEqual(report["file_entries"][0]["name"], "MAP_1_1C.BIN")

    def test_bad_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "bad.bin"
            create_image(image, bad_sync=True)
            with self.assertRaises(ValueError):
                SaturnISO(image).inspect()

    def test_out_of_range_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "bad.bin"
            create_image(image, outside=True)
            with self.assertRaises(ValueError):
                SaturnISO(image).inspect()

    def test_corrupt_endianness(self):
        with self.assertRaises(ValueError):
            both32(bytes((1, 0, 0, 0, 0, 0, 0, 2)), 0)

    def test_short_track(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "bad.bin"
            image.write_bytes(b"not a disc")
            with self.assertRaises(ValueError):
                SaturnISO(image)


if __name__ == "__main__":
    unittest.main()
