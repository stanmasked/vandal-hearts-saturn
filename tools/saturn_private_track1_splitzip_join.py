#!/usr/bin/env python3
"""Stage97: securely reconstruct a user-owned Track1 from split ZIP volumes.

Handles one standard ZIP split byte-for-byte into .zip.001, .zip.002, etc.
Unlike independent ZIP files, the parts are NOT opened as separate archives.
Neither the user's original Track1 nor its parts belong in public Git/CI.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import zipfile

from tools.saturn_private_capture_session import PINNED, _not_in_checkout

MAX_VOLUME = 256 * 1024 * 1024
MAX_COMPRESSED = 1024 * 1024 * 1024
BLOCK = 2 * 1024 * 1024
VOLUME = re.compile(r"(.+\.zip)\.([0-9]{3})\Z", re.IGNORECASE)


def _safe_private_directory(directory: Path) -> None:
    if (not directory.is_absolute() or directory.is_symlink() or
            not directory.is_dir() or
            stat.S_IMODE(directory.stat().st_mode) & 0o077):
        raise ValueError("private directory must have 0700 permissions")
    _not_in_checkout(directory)


def _inspect_volumes(volumes: list[Path]) -> list[Path]:
    if not isinstance(volumes, list) or not 2 <= len(volumes) <= 999:
        raise ValueError("two or more split ZIP volumes required")
    base = None
    ordered = {}
    used_inodes = set()
    for candidate in volumes:
        if not isinstance(candidate, Path) or not candidate.is_absolute():
            raise ValueError("absolute private volume paths required")
        _safe_private_directory(candidate.parent)
        info = candidate.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                info.st_size <= 0 or info.st_size >= MAX_VOLUME):
            raise ValueError("volume must be an unlinked regular file under 256MiB")
        match = VOLUME.fullmatch(candidate.name)
        if not match:
            raise ValueError("not a .zip.NNN split volume")
        prefix, number = match.groups()
        if base is None:
            base = prefix
        if base != prefix:
            raise ValueError("split-volume names differ")
        index = int(number)
        if index in ordered or index < 1 or index > len(volumes):
            raise ValueError("duplicate or out-of-order volume index")
        identity = (info.st_dev, info.st_ino)
        if identity in used_inodes:
            raise ValueError("archive volume inode reused")
        used_inodes.add(identity)
        ordered[index] = candidate
    if set(ordered) != set(range(1, len(volumes) + 1)):
        raise ValueError("split ZIP volume missing")
    ordered_volumes = [ordered[i] for i in range(1, len(volumes) + 1)]
    if sum(x.stat().st_size for x in ordered_volumes) > MAX_COMPRESSED:
        raise ValueError("split archive exceeds bounded maximum")
    return ordered_volumes


def join_split_zip(
    volumes: list[Path], output: Path, *,
    expected: tuple[int, str] | None = None,
) -> dict:
    """Verify ZIP CRC + full pinned SHA256; expose only the finished .bin."""
    if expected is None:
        expected = PINNED["track1"]
    if (not isinstance(expected, tuple) or len(expected) != 2 or
            type(expected[0]) is not int or expected[0] <= 0 or
            expected[0] % 2352 or
            not isinstance(expected[1], str) or
            not re.fullmatch("[0-9a-f]{64}", expected[1])):
        raise ValueError("invalid independent Track1 size/SHA256 pin")
    if (not isinstance(output, Path) or not output.is_absolute() or
            output.is_symlink() or output.exists() or
            output.suffix.lower() != ".bin"):
        raise ValueError("new, absolute private .bin output required")
    _safe_private_directory(output.parent)
    ordered = _inspect_volumes(volumes)
    if output.parent.resolve() in {p.parent.resolve() for p in ordered}:
        raise ValueError("output must not share volume folder")
    joined = output.parent / ("." + secrets.token_hex(16) + ".joined")
    partial = output.parent / ("." + secrets.token_hex(16) + ".partial")
    identities = []
    combined = hashlib.sha256()
    bytes_written = 0
    try:
        joined_fd = os.open(joined, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(joined_fd, "wb") as dest:
            for part in ordered:
                before = part.stat()
                identity = (before.st_dev, before.st_ino, before.st_size,
                            before.st_mtime_ns, before.st_ctime_ns)
                identities.append(identity)
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                fd = os.open(part, flags)
                with os.fdopen(fd, "rb") as source:
                    count = 0
                    while block := source.read(BLOCK):
                        count += len(block)
                        dest.write(block)
                after = part.stat()
                after_id = (after.st_dev, after.st_ino, after.st_size,
                            after.st_mtime_ns, after.st_ctime_ns)
                if identity != after_id or count != before.st_size:
                    raise ValueError("split volume modified during read")
            dest.flush()
            os.fsync(dest.fileno())
        with zipfile.ZipFile(joined) as archive:
            entries = archive.infolist()
            if len(entries) != 1:
                raise ValueError("split ZIP must contain exactly one file")
            member = entries[0]
            if (member.is_dir() or
                    member.file_size != expected[0] or
                    member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) or
                    member.flag_bits & 1 or
                    member.filename != output.name):
                raise ValueError("split archive member invalid or wrong filename")
            fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as output_stream:
                with archive.open(member, "r") as source:
                    while block := source.read(BLOCK):
                        bytes_written += len(block)
                        if bytes_written > expected[0]:
                            raise ValueError("uncompressed Track1 exceeds expected size")
                        combined.update(block)
                        output_stream.write(block)
                output_stream.flush()
                os.fsync(output_stream.fileno())
                if (bytes_written != expected[0] or
                        combined.hexdigest() != expected[1] or
                        os.fstat(output_stream.fileno()).st_size != expected[0]):
                    raise ValueError("complete reconstructed Track1 SHA256 mismatch")
                os.fchmod(output_stream.fileno(), 0o400)
        for part, old in zip(ordered, identities):
            now = part.stat()
            if old != (now.st_dev, now.st_ino, now.st_size,
                       now.st_mtime_ns, now.st_ctime_ns):
                raise ValueError("split ZIP volume modified during extraction")
        os.link(partial, output)
        return {
            "schema_version": 1,
            "kind": "STAGE97_PRIVATE_SPLIT_ZIP_VERIFICATION_ONLY",
            "split_volume_count": len(ordered),
            "reconstructed_track1_bytes": bytes_written,
            "zip_member_crc_validated": True,
            "full_stage02_track1_sha256_verified": True,
            "original_game_boot_verified": False,
            "source_gameplay_or_map_verified": False,
            "media_uploaded_to_public_git": False,
        }
    finally:
        for temp in (joined, partial):
            try:
                temp.unlink()
            except FileNotFoundError:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--part", type=Path, action="append", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        receipt = join_split_zip(args.part, args.output)
    except (OSError, ValueError, TypeError, zipfile.BadZipFile,
            zipfile.LargeZipFile, RuntimeError):
        print("STAGE97_PRIVATE_SPLIT_ZIP_VERIFY_REJECTED", file=sys.stderr)
        return 1
    print("STAGE97_FULL_STAGE02_TRACK1_SHA256_PASS "
          f"parts={receipt['split_volume_count']} bytes={receipt['reconstructed_track1_bytes']} "
          "original_game_boot=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
