#!/usr/bin/env python3
"""Stage92: private, read-only Google Drive Range retrieval for the *already owned* Track1.

No OAuth tokens, media bytes, file paths or private hashes are printed.
This tool is for use on a trusted local machine with a separate Google Drive
OAuth bearer token. It cannot use ChatGPT's Drive connector credentials.
It never writes any user data into the git working tree or CI artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
from pathlib import Path
import re
import secrets
import stat
import sys
from typing import Callable
from urllib import error, parse, request

from tools.saturn_private_capture_session import PINNED, _not_in_checkout

TRACK1_SIZE, TRACK1_SHA256 = PINNED["track1"]
DEFAULT_CHUNK = 8 * 1024 * 1024
MIN_CHUNK = 4096
MAX_CHUNK = 16 * 1024 * 1024
CONTENT_RANGE = re.compile(r"bytes ([0-9]+)-([0-9]+)/([0-9]+)\Z", re.ASCII)
DRIVE_FILE_ID = re.compile(r"[A-Za-z0-9_-]{10,180}\Z")
READ_BLOCK = 256 * 1024


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("refusing download redirect")


def private_destination(path: Path) -> None:
    if not path.is_absolute() or path.suffix.lower() != ".bin" or not path.name:
        raise ValueError("expected absolute private .bin destination")
    parent = path.parent
    _not_in_checkout(parent)
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("private parent directory missing or redirected")
    perms = stat.S_IMODE(parent.stat().st_mode)
    if perms & 0o077:
        raise ValueError("private parent must have mode 0700")
    if path.exists() or path.is_symlink():
        raise ValueError("refusing to overwrite or follow an existing output")


def get_private_range(file_id: str, token: str, first: int, last: int):
    """Return context-managed HTTPS response; secrets only in Authorization."""
    if DRIVE_FILE_ID.fullmatch(file_id) is None or not token:
        raise ValueError("invalid file id or missing local OAuth token")
    if not 0 <= first <= last < TRACK1_SIZE:
        raise ValueError("requested range outside pinned Track1")
    url = ("https://www.googleapis.com/drive/v3/files/"
           + parse.quote(file_id, safe="") + "?alt=media")
    req = request.Request(
        url,
        headers={"Authorization": "Bearer " + token,
                 "Range": f"bytes={first}-{last}",
                 "Accept-Encoding": "identity"},
        method="GET",
    )
    return request.build_opener(NoRedirect()).open(req, timeout=45)


def _header(headers, key: str):
    # Works with EmailMessage from urllib and plain test mappings.
    for name, value in headers.items():
        if name.lower() == key.lower():
            return str(value).strip()
    return None


def retrieve_private_track1(
    destination: Path,
    response_factory: Callable[[int, int], object],
    *,
    expected_bytes: int = TRACK1_SIZE,
    expected_sha256: str = TRACK1_SHA256,
    chunk_bytes: int = DEFAULT_CHUNK,
) -> dict:
    """Stream and atomically expose a complete verified file, never partial bytes.

    The injected response_factory allows invented-only unit tests with no
    network/OAuth, while the CLI uses Google Drive's authenticated GET Range.
    """
    if (type(expected_bytes) is not int or expected_bytes <= 0 or
            expected_bytes % 2352 != 0 or
            not isinstance(expected_sha256, str) or
            not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)):
        raise ValueError("invalid pinned source size or full SHA-256")
    if not MIN_CHUNK <= chunk_bytes <= MAX_CHUNK:
        raise ValueError("chunk limit out of bounds")
    private_destination(destination)
    partial = destination.parent / ("." + secrets.token_hex(20) + ".partial")
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    bytes_received = 0
    chunks = 0
    etag = None
    h = hashlib.sha256()
    try:
        with os.fdopen(fd, "wb") as output:
            while bytes_received < expected_bytes:
                first = bytes_received
                last = min(first + chunk_bytes, expected_bytes) - 1
                with response_factory(first, last) as response:
                    if getattr(response, "status", None) != 206:
                        raise ValueError("server did not honor exact HTTP Range")
                    value = _header(response.headers, "Content-Range")
                    match = CONTENT_RANGE.fullmatch(value or "")
                    if not match or tuple(map(int, match.groups())) != (
                        first, last, expected_bytes
                    ):
                        raise ValueError("unexpected Content-Range")
                    content_encoding = _header(response.headers, "Content-Encoding")
                    if content_encoding and content_encoding.lower() != "identity":
                        raise ValueError("compressed/encoded responses are refused")
                    got_etag = _header(response.headers, "ETag")
                    if got_etag:
                        if etag is not None and got_etag != etag:
                            raise ValueError("Drive object changed between ranges")
                        etag = got_etag
                    remaining = last - first + 1
                    while remaining:
                        block = response.read(min(READ_BLOCK, remaining))
                        if not block:
                            raise ValueError("truncated range response")
                        if len(block) > remaining:
                            raise ValueError("range response exceeded requested length")
                        output.write(block)
                        h.update(block)
                        remaining -= len(block)
                    if response.read(1):
                        raise ValueError("server returned extra unexpected bytes")
                bytes_received = last + 1
                chunks += 1
            output.flush()
            os.fsync(output.fileno())
            if h.hexdigest() != expected_sha256:
                raise ValueError("complete Track1 SHA-256 mismatch")
            if os.fstat(output.fileno()).st_size != expected_bytes:
                raise ValueError("complete Track1 size mismatch")
            os.fchmod(output.fileno(), 0o400)
        # Link fails if another process created the destination; never replace.
        os.link(partial, destination)
        os.unlink(partial)
        return {
            "source": "private_range_retrieval",
            "track1_expected_full_sha256_verified": True,
            "track1_bytes_verified": bytes_received,
            "independent_range_responses": chunks,
            "local_private_output_created": True,
            "public_upload_performed": False,
            "original_saturn_game_boot_verified": False,
            "first_battle_scene_verified": False,
        }
    finally:
        try:
            partial.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drive-file-id", required=True, help="Private Drive file ID, never printed")
    parser.add_argument("--output", type=Path, required=True, help="Private 0700 folder / Track1.bin")
    parser.add_argument("--chunk-mib", type=int, default=8)
    parser.add_argument("--token-env", default="GOOGLE_DRIVE_ACCESS_TOKEN",
                        help="Name of locally available OAuth token environment variable")
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", args.token_env):
            raise ValueError("invalid environment variable name")
        token = os.environ.get(args.token_env, "")
        if not token:
            raise ValueError("local Google Drive OAuth token unavailable")
        if DRIVE_FILE_ID.fullmatch(args.drive_file_id) is None:
            raise ValueError("invalid private Drive file identifier")
        result = retrieve_private_track1(
            args.output,
            lambda first, last: get_private_range(
                args.drive_file_id, token, first, last
            ),
            chunk_bytes=args.chunk_mib * 1024 * 1024,
        )
    except (OSError, ValueError, error.URLError):
        # Never emit request objects or exceptions: they may contain OAuth data.
        print("STAGE92_PRIVATE_TRACK1_RANGE_VERIFY_REJECTED", file=sys.stderr)
        return 1
    print("STAGE92_PRIVATE_TRACK1_FULL_SHA256_VERIFIED "
          f"bytes={result['track1_bytes_verified']} ranges={result['independent_range_responses']} "
          "game_boot_verified=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
