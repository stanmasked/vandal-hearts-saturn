"""Stage92: invented byte-stream tests for strict private Google Drive HTTP Range handling."""
from __future__ import annotations

import hashlib
from io import BytesIO
import os
from pathlib import Path
import tempfile
import unittest

from tools.saturn_private_track1_range_retrieval import (
    MIN_CHUNK, NoRedirect, private_destination, retrieve_private_track1,
)


class FakeResponse(BytesIO):
    status = 206

    def __init__(self, data, start, stop, total, *, status=206,
                 content_range=None, etag='"test-pinned"', encoding=None):
        super().__init__(data)
        self.status = status
        self.headers = {
            "Content-Range": content_range or f"bytes {start}-{stop}/{total}"
        }
        if etag is not None:
            self.headers["ETag"] = etag
        if encoding is not None:
            self.headers["Content-Encoding"] = encoding


class RangeVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        self.output = self.root / "invented-track.bin"
        # Invented RAW-sector-aligned bytes, never from a game image.
        self.content = bytes((i * 17 + 31) % 256 for i in range(2352 * 7))
        self.sha = hashlib.sha256(self.content).hexdigest()
        self.called = []

    def factory(self, a, b):
        self.called.append((a, b))
        return FakeResponse(self.content[a:b+1], a, b, len(self.content))

    def verify(self, factory=None):
        return retrieve_private_track1(
            self.output, factory or self.factory,
            expected_bytes=len(self.content),
            expected_sha256=self.sha,
            chunk_bytes=MIN_CHUNK,
        )

    def test_successful_independent_ranges_and_private_mode(self):
        receipt = self.verify()
        self.assertGreaterEqual(len(self.called), 4)
        self.assertEqual(self.called[0], (0, MIN_CHUNK - 1))
        self.assertEqual(self.called[-1][1], len(self.content) - 1)
        self.assertEqual(self.output.read_bytes(), self.content)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o400)
        self.assertTrue(receipt["track1_expected_full_sha256_verified"])
        self.assertFalse(receipt["original_saturn_game_boot_verified"])
        self.assertEqual(
            {p.name for p in self.root.iterdir()}, {self.output.name},
        )

    def test_wrong_sha256_never_exposes_partial_result(self):
        with self.assertRaises(ValueError):
            retrieve_private_track1(
                self.output, self.factory,
                expected_bytes=len(self.content),
                expected_sha256="0" * 64,
                chunk_bytes=MIN_CHUNK,
            )
        self.assertEqual(list(self.root.iterdir()), [])

    def test_range_200_is_refused(self):
        def wrong(a, b):
            return FakeResponse(self.content[a:b+1], a, b,
                                len(self.content), status=200)
        with self.assertRaises(ValueError):
            self.verify(wrong)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_wrong_content_range_or_missing_bytes_is_rejected(self):
        def wrong(a, b):
            return FakeResponse(self.content[a:b], a, b, len(self.content))
        with self.assertRaises(ValueError):
            self.verify(wrong)
        self.assertFalse(self.output.exists())

    def test_extra_bytes_are_rejected(self):
        def wrong(a, b):
            return FakeResponse(self.content[a:b+1] + b"leak", a, b,
                                len(self.content))
        with self.assertRaises(ValueError):
            self.verify(wrong)
        self.assertFalse(self.output.exists())

    def test_mutating_etag_is_rejected(self):
        def wrong(a, b):
            return FakeResponse(self.content[a:b+1], a, b,
                                len(self.content),
                                etag='"a"' if a == 0 else '"b"')
        with self.assertRaises(ValueError):
            self.verify(wrong)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_encoded_responses_are_rejected(self):
        def wrong(a, b):
            return FakeResponse(self.content[a:b+1], a, b,
                                len(self.content), encoding="gzip")
        with self.assertRaises(ValueError):
            self.verify(wrong)
        self.assertFalse(self.output.exists())

    def test_reuse_existing_destination_does_not_overwrite(self):
        self.output.write_bytes(b"original")
        with self.assertRaises(ValueError):
            self.verify()
        self.assertEqual(self.output.read_bytes(), b"original")

    def test_reject_checkout_and_world_readable_directory(self):
        (self.root / ".git").mkdir()
        with self.assertRaises(ValueError):
            private_destination(self.output)
        (self.root / ".git").rmdir()
        self.root.chmod(0o755)
        with self.assertRaises(ValueError):
            private_destination(self.output)

    def test_reject_symlink_destination(self):
        target = self.root / "target"
        target.write_bytes(b"safe")
        self.output.symlink_to(target)
        with self.assertRaises(ValueError):
            self.verify()
        self.assertEqual(target.read_bytes(), b"safe")

    def test_invalid_size_hash_and_chunk_are_rejected(self):
        for size in (-1, 0, 2353, True):
            with self.subTest(size=size), self.assertRaises(ValueError):
                retrieve_private_track1(
                    self.output, self.factory,
                    expected_bytes=size, expected_sha256=self.sha,
                )
        for sha in ("wrong", "F" * 64, "", None):
            with self.subTest(sha=sha), self.assertRaises(ValueError):
                retrieve_private_track1(
                    self.output, self.factory,
                    expected_bytes=len(self.content), expected_sha256=sha,
                )
        for chunk in (0, MIN_CHUNK - 1, 32 * 1024 * 1024):
            with self.subTest(chunk=chunk), self.assertRaises(ValueError):
                retrieve_private_track1(
                    self.output, self.factory,
                    expected_bytes=len(self.content),
                    expected_sha256=self.sha, chunk_bytes=chunk,
                )

    def test_redirect_requests_are_disabled(self):
        from urllib import request
        manager = NoRedirect()
        req = request.Request("https://www.googleapis.com/drive/v3/files/abc",
                              headers={"Authorization": "Bearer secret"})
        with self.assertRaises(ValueError):
            manager.redirect_request(
                req, None, 302, "Found", {},
                "https://untrusted.example.org/collect",
            )


if __name__ == "__main__":
    unittest.main()
