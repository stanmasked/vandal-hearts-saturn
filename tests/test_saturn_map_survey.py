"""Synthetic, no-original-data tests for Saturn .MAP metadata survey."""
import hashlib
import unittest
from io import BytesIO

from tools.saturn_map_survey import profile, file_family, read_file_payload


class FakeIso:
    sectors = 3

    @staticmethod
    def sector(stream, lba):
        if lba not in (0, 1, 2):
            raise ValueError('bad sector')
        stream.seek(lba * 2048)
        return stream.read(2048)


class MapSurveyTests(unittest.TestCase):
    def test_profile_only_numeric_metadata(self):
        synthetic = bytes.fromhex('000c002400300030cdcd') + b'PRIVATE-TEST-MARKER' + bytes(100)
        item = profile('M_MAP01.MAP', synthetic)
        self.assertEqual(item['family'], 'M_MAP')
        self.assertEqual(item['first_five_be16'], [12, 36, 48, 48, 52685])
        self.assertEqual(item['sha256'], hashlib.sha256(synthetic).hexdigest())
        self.assertNotIn('PRIVATE-TEST-MARKER', str(item))
        self.assertEqual(sum(item['nonzero_per_16k']), sum(x != 0 for x in synthetic))

    def test_odd_length(self):
        item = profile('M_IVE01.MAP', bytes(range(13)))
        self.assertEqual(item['length_bytes'], 13)

    def test_short_input_rejected(self):
        with self.assertRaises(ValueError):
            profile('x.MAP', bytes(9))

    def test_family_names(self):
        self.assertEqual(file_family('M_KEY17.MAP'), 'M_KEY')
        self.assertEqual(file_family('M_SHOW.MAP'), 'OTHER')

    def test_file_bounds(self):
        iso = FakeIso()
        stream = BytesIO(b'a' * 2048 + b'b' * 2048 + b'c' * 2048)
        self.assertEqual(read_file_payload(iso, stream, {'lba': 1, 'bytes': 2050}),
                         b'b' * 2048 + b'cc')
        for entry in ({'lba': 2, 'bytes': 2050},
                      {'lba': 0, 'bytes': 9_999_999},
                      {'lba': -1, 'bytes': 1}):
            with self.assertRaises(ValueError):
                read_file_payload(iso, stream, entry)


if __name__ == '__main__':
    unittest.main()
