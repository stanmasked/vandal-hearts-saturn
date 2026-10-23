#!/usr/bin/env python3
"""Stage126: offline, fail-closed verification of a *privately* restored Stage124 tar.gz.

No disc, screenshots, archive payloads, or private fingerprints belong in public CI.
This tool checks local bytes only: it CANNOT assert that Google Drive stored the file.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import sys
import tarfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
FRAME = re.compile(r"frame-(\d+)\.png\Z")
PNG_SIG = b"\x89PNG\r\n\x1a\n"
MAX_FILES = 4096
MAX_TOTAL = 2_000_000_000
MAX_MEMBER = 100_000_000
MAX_PNG = 8 * 1024 * 1024
SIDECARS = frozenset(("pre.png", "post.png", "frames.stats", "fad.vhcdlog",
                      "pad-events.txt", "pad-state.txt", "sh2-window.txt", "video-state.txt"))


def _private_fingerprint(path: Path) -> tuple[int, str, tuple[int, ...]]:
    if (not path.is_absolute() or path.is_symlink() or path == ROOT
            or ROOT in path.parents or ROOT in path.resolve().parents):
        raise ValueError("absolute private archive outside checkout required")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError("private archive unavailable") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError("archive must be a unique regular file")
        digest = hashlib.sha256()
        n = 0
        while block := os.read(fd, 1024 * 1024):
            digest.update(block)
            n += len(block)
        after = os.fstat(fd)
        identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
        if n != after.st_size or identity(before) != identity(after):
            raise ValueError("archive changed while fingerprinting")
        return n, digest.hexdigest(), identity(after)
    finally:
        os.close(fd)



def _png_integrity(raw: bytes) -> tuple[int, int]:
    """Validate PNG structure, dimensions and CRCs, not scene content."""
    if len(raw) > MAX_PNG or len(raw) < 57 or not raw.startswith(PNG_SIG):
        raise ValueError("invalid PNG framing")
    offset = 8
    ihdr = idat = iend = False
    width = height = 0
    while offset + 12 <= len(raw):
        size = struct.unpack_from(">I", raw, offset)[0]
        end = offset + 12 + size
        if size > MAX_PNG or end > len(raw):
            raise ValueError("invalid PNG chunk bounds")
        kind = raw[offset+4:offset+8]
        data = raw[offset+8:offset+8+size]
        crc = struct.unpack_from(">I", raw, offset+8+size)[0]
        if zlib.crc32(kind + data) & 0xffffffff != crc:
            raise ValueError("invalid PNG chunk CRC")
        if not ihdr:
            if kind != b"IHDR" or size != 13:
                raise ValueError("invalid PNG header order")
            width, height, depth, color, cm, fm, interlace = struct.unpack(">IIBBBBB", data)
            if (not 64 <= width <= 704 or not 64 <= height <= 512
                    or depth not in (1, 2, 4, 8, 16)
                    or color not in (0, 2, 3, 4, 6)
                    or (color in (2, 4, 6) and depth not in (8, 16))
                    or (color == 3 and depth not in (1, 2, 4, 8))
                    or (cm, fm) != (0, 0) or interlace not in (0, 1)):
                raise ValueError("invalid PNG dimensions or color format")
            ihdr = True
        elif kind == b"IHDR":
            raise ValueError("duplicate PNG header")
        if kind == b"IDAT":
            idat = True
        if kind == b"IEND":
            if size != 0 or not idat or end != len(raw):
                raise ValueError("invalid PNG footer")
            iend = True
            break
        offset = end
    if not (ihdr and idat and iend):
        raise ValueError("incomplete PNG structure")
    return width, height


def _members_are_safe(archive: Path, expected_checkpoints: int) -> tuple[int, int]:
    found: dict[PurePosixPath, set[int]] = {}
    sidecars: dict[PurePosixPath, set[str]] = {}
    names: set[str] = set()
    files = 0
    payload_size = 0
    try:
        with tarfile.open(archive, "r:gz") as tar:
            for entry in tar:
                name = entry.name
                if (not name or len(name) > 320 or "\\" in name or name.startswith("/")
                        or any(part in ("..", "") for part in name.split("/"))
                        or any(ord(ch) < 32 for ch in name)):
                    raise ValueError("unsafe archive path")
                normalized = PurePosixPath(name)
                if name in names:
                    raise ValueError("duplicate archive member")
                names.add(name)
                if len(names) > MAX_FILES:
                    raise ValueError("archive has too many members")
                if entry.isdir():
                    continue
                if not entry.isfile() or entry.size < 0 or entry.size > MAX_MEMBER:
                    raise ValueError("archive has unsafe member type or size")
                files += 1
                payload_size += entry.size
                if payload_size > MAX_TOTAL:
                    raise ValueError("archive expands beyond private safety bound")
                frame = FRAME.fullmatch(normalized.name)
                if frame:
                    index = int(frame.group(1))
                    if not 1 <= index <= 108000:
                        raise ValueError("checkpoint outside Stage124 frame limit")
                    folder = normalized.parent
                    if folder == PurePosixPath("."):
                        raise ValueError("checkpoint has no cohort directory")
                    group = found.setdefault(folder, set())
                    if index in group:
                        raise ValueError("duplicate cohort checkpoint")
                    group.add(index)
                elif normalized.name in SIDECARS:
                    sidecars.setdefault(normalized.parent, set()).add(normalized.name)
                stream = tar.extractfile(entry)
                if stream is None:
                    raise ValueError("unreadable archive member")
                with stream:
                    if frame or normalized.name in ("pre.png", "post.png"):
                        if entry.size > MAX_PNG:
                            raise ValueError("PNG checkpoint size exceeds bound")
                        payload = stream.read(entry.size + 1)
                        if len(payload) != entry.size:
                            raise ValueError("incomplete archive PNG")
                        _png_integrity(payload)
                    else:
                        read = 0
                        while block := stream.read(1024 * 1024):
                            read += len(block)
                        if read != entry.size:
                            raise ValueError("incomplete archive member")
        if len(found) != 2:
            raise ValueError("expected two independent Stage124 cohorts")
        frames = set(range(120, 120 * (expected_checkpoints + 1), 120))
        if any(group != frames for group in found.values()):
            raise ValueError("Stage124 checkpoint sequence incomplete")
        if any(sidecars.get(folder) != SIDECARS for folder in found):
            raise ValueError("Stage124 cohort diagnostics missing")
        if files < 2 * expected_checkpoints + 2 * len(SIDECARS):
            raise ValueError("Stage124 diagnostics or inventory missing")
        # Drain the gzip stream, including its footer, to reject a truncated or
        # corrupt compressed tail that an early tar end-marker might conceal.
        expanded = 0
        with gzip.open(archive, "rb") as decompressor:
            while block := decompressor.read(1024 * 1024):
                expanded += len(block)
                if expanded > MAX_TOTAL:
                    raise ValueError("compressed archive expansion exceeds bound")
    except (tarfile.TarError, EOFError, OSError, gzip.BadGzipFile) as exc:
        raise ValueError("private archive structure or compression invalid") from exc
    return files, 2 * expected_checkpoints


def verify_private_stage124_archive(archive: Path, *, expected_size: int,
                                    expected_sha256: str, checkpoints: int = 900) -> dict:
    if type(expected_size) is not int or expected_size <= 0 or expected_size > MAX_TOTAL:
        raise ValueError("private expected archive size invalid")
    if not isinstance(expected_sha256, str) or not SHA256.fullmatch(expected_sha256):
        raise ValueError("private expected archive SHA-256 invalid")
    if type(checkpoints) is not int or checkpoints < 1 or checkpoints > 900:
        raise ValueError("checkpoint bound invalid")
    before = _private_fingerprint(archive)
    if (before[0], before[1]) != (expected_size, expected_sha256):
        raise ValueError("archive differs from supplied expected fingerprint")
    files, pngs = _members_are_safe(archive, checkpoints)
    if _private_fingerprint(archive) != before:
        raise ValueError("archive mutated during inspection")
    return {"stage": 124, "archive_matches_supplied_fingerprint": True,
            "archive_bytes": expected_size, "regular_members": files,
            "checkpoint_pngs": pngs, "cohorts": 2,
            "drive_upload_and_readback_verified": False}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--expected-size", type=int, required=True,
                   help="Get from owner-only Stage124 private manifest, never public logs")
    p.add_argument("--expected-sha256", required=True,
                   help="Get from owner-only Stage124 private manifest, never public logs")
    a = p.parse_args()
    try:
        report = verify_private_stage124_archive(a.archive, expected_size=a.expected_size,
                                                expected_sha256=a.expected_sha256)
    except (ValueError, OSError):
        print("STAGE126_PRIVATE_ARCHIVE_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
