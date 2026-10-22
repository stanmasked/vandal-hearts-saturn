#!/usr/bin/env python3
"""Stage97: split a private, user-owned Saturn Track1 into small independent ZIPs.

Use the local original Track1 only. The five 128-MiB ZIP pieces plus a
private manifest can then be stored in the user's existing private Drive
folder. Nothing here uploads media, creates public artifacts or prints hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import zipfile

from tools.saturn_private_capture_session import PINNED, _fingerprint, _not_in_checkout

CHUNK_BYTES = 128 * 1024 * 1024
MIN_CHUNK = 4096
MAX_CHUNK = 160 * 1024 * 1024
TRANSFER_LIMIT = 256 * 1024 * 1024
MANIFEST = "track1-private-parts.json"
MANIFEST_KIND = "STAGE97_USER_OWNED_TRACK1_SPLIT_ARCHIVES"
HEX = re.compile(r"[0-9a-f]{64}\Z")
ARCHIVE = re.compile(r"track1-part-([0-9]{3})\.zip\Z")
MEMBER = re.compile(r"track1-part-([0-9]{3})\.raw\Z")
IO_BLOCK = 1024 * 1024


def _private_dir(path: Path, *, empty=False):
    if not isinstance(path, Path) or not path.is_absolute() or path.is_symlink():
        raise ValueError("absolute private directory required")
    _not_in_checkout(path)
    if not path.is_dir() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("private directory must exist with mode 0700")
    if empty and any(path.iterdir()):
        raise ValueError("private output folder must initially be empty")


def _private_path(path: Path):
    if not isinstance(path, Path) or not path.is_absolute() or path.is_symlink():
        raise ValueError("absolute private regular source required")
    _not_in_checkout(path)
    if (not path.is_file() or not stat.S_ISREG(path.lstat().st_mode) or
            path.stat().st_nlink != 1):
        raise ValueError("source must not be symlinked or hardlinked")


def _file_digest(path: Path):
    size, digest, identity = _fingerprint(path)
    return size, digest, identity


def _pinned(expected=None):
    values = PINNED["track1"] if expected is None else expected
    if (not isinstance(values, tuple) or len(values) != 2 or
            type(values[0]) is not int or values[0] <= 0 or
            values[0] % 2352 or not isinstance(values[1], str) or
            HEX.fullmatch(values[1]) is None):
        raise ValueError("invalid source identity pin")
    return values


def _zip_info(index):
    info = zipfile.ZipInfo(f"track1-part-{index:03d}.raw",
                           date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o600 << 16
    return info


def split_private_track1(
    track1: Path, directory: Path, *,
    chunk_bytes=CHUNK_BYTES, expected=None,
) -> dict:
    size_pin, sha_pin = _pinned(expected)
    if (type(chunk_bytes) is not int or not MIN_CHUNK <= chunk_bytes <= MAX_CHUNK):
        raise ValueError("unsupported chunk size")
    _private_path(track1)
    _private_dir(directory, empty=True)
    if track1.parent.resolve() == directory.resolve():
        raise ValueError("source cannot reside inside parts output directory")
    before = _file_digest(track1)
    if before[:2] != (size_pin, sha_pin):
        raise ValueError("original Track1 failed Stage02 SHA-256/size pin")
    count = (size_pin + chunk_bytes - 1) // chunk_bytes
    if count > 999:
        raise ValueError("too many archive chunks")
    completed = []
    records = []
    digest = hashlib.sha256()
    try:
        with track1.open("rb") as source:
            for i in range(count):
                archive_name = f"track1-part-{i:03d}.zip"
                path = directory / archive_name
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                completed.append(path)
                length = min(chunk_bytes, size_pin - i * chunk_bytes)
                part = hashlib.sha256()
                with os.fdopen(fd, "wb") as file:
                    with zipfile.ZipFile(file, "w", allowZip64=True) as zipped:
                        with zipped.open(_zip_info(i), "w", force_zip64=True) as member:
                            left = length
                            while left:
                                block = source.read(min(IO_BLOCK, left))
                                if not block:
                                    raise ValueError("Track1 truncated during archive split")
                                digest.update(block)
                                part.update(block)
                                member.write(block)
                                left -= len(block)
                    file.flush()
                    os.fsync(file.fileno())
                archive_size, archive_sha, _ = _file_digest(path)
                if archive_size >= TRANSFER_LIMIT:
                    raise ValueError("archive exceeds connected Drive transfer limit")
                records.append({
                    "archive": archive_name,
                    "archive_bytes": archive_size,
                    "archive_sha256": archive_sha,
                    "member": f"track1-part-{i:03d}.raw",
                    "member_bytes": length,
                    "member_sha256": part.hexdigest(),
                })
            if source.read(1):
                raise ValueError("source has unexpected trailing bytes")
        after = _file_digest(track1)
        if before != after or digest.hexdigest() != sha_pin:
            raise ValueError("original Track1 changed while splitting")
        manifest = {
            "schema_version": 1,
            "kind": MANIFEST_KIND,
            "track1_basename": track1.name,
            "track1_bytes": size_pin,
            "track1_sha256": sha_pin,
            "chunk_bytes": chunk_bytes,
            "parts": records,
        }
        target = directory / MANIFEST
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        fd = os.open(target, flags, 0o600)
        completed.append(target)
        with os.fdopen(fd, "wb") as f:
            f.write((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        for output in completed:
            try:
                output.unlink()
            except OSError:
                pass
        raise
    return {
        "kind": "STAGE97_PRIVATE_SPLIT_ONLY",
        "verified_track1_bytes": size_pin,
        "zip_archives_created": count,
        "all_archives_smaller_than_256_mib": True,
        "reassembly_verified": False,
        "original_game_boot_verified": False,
        "uploaded_to_drive": False,
    }


def _manifest(directory: Path, expected: tuple):
    _private_dir(directory)
    path = directory / MANIFEST
    _private_path(path)
    if path.stat().st_size > 256 * 1024 or path.stat().st_size <= 0:
        raise ValueError("part manifest missing or too large")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("invalid private manifest") from exc
    size_pin, sha_pin = expected
    if (not isinstance(doc, dict) or set(doc) != {
            "schema_version", "kind", "track1_basename",
            "track1_bytes", "track1_sha256", "chunk_bytes", "parts"
        } or doc["schema_version"] != 1 or doc["kind"] != MANIFEST_KIND or
            doc["track1_bytes"] != size_pin or doc["track1_sha256"] != sha_pin or
            not isinstance(doc["track1_basename"], str) or
            Path(doc["track1_basename"]).name != doc["track1_basename"] or
            doc["track1_basename"] in (".", "..") or
            type(doc["chunk_bytes"]) is not int or not
            MIN_CHUNK <= doc["chunk_bytes"] <= MAX_CHUNK or
            not isinstance(doc["parts"], list)):
        raise ValueError("manifest identity or schema does not match Stage02")
    parts = doc["parts"]
    if (len(parts) != (size_pin + doc["chunk_bytes"] - 1) // doc["chunk_bytes"] or
            len(parts) > 999):
        raise ValueError("incomplete or duplicate archive list")
    for i, part in enumerate(parts):
        expected_archive = f"track1-part-{i:03d}.zip"
        expected_member = f"track1-part-{i:03d}.raw"
        expected_length = min(
            doc["chunk_bytes"], size_pin - i * doc["chunk_bytes"]
        )
        if (not isinstance(part, dict) or set(part) != {
                "archive", "archive_bytes", "archive_sha256", "member",
                "member_bytes", "member_sha256"
            } or part["archive"] != expected_archive or
                part["member"] != expected_member or
                type(part["member_bytes"]) is not int or
                part["member_bytes"] != expected_length or
                type(part["archive_bytes"]) is not int or
                not 0 < part["archive_bytes"] < TRANSFER_LIMIT or
                not isinstance(part["archive_sha256"], str) or
                HEX.fullmatch(part["archive_sha256"]) is None or
                not isinstance(part["member_sha256"], str) or
                HEX.fullmatch(part["member_sha256"]) is None):
            raise ValueError("unexpected archive name, size or hash")
    if {p.name for p in directory.iterdir()} != (
        {MANIFEST} | {part["archive"] for part in parts}
    ):
        raise ValueError("unexpected or missing files in private archive folder")
    return doc


def join_private_track1(directory: Path, output: Path, *, expected=None) -> dict:
    size_pin, sha_pin = _pinned(expected)
    doc = _manifest(directory, (size_pin, sha_pin))
    if (not isinstance(output, Path) or not output.is_absolute() or
            output.is_symlink() or output.exists() or
            output.name != doc["track1_basename"] or
            output.suffix.lower() != ".bin"):
        raise ValueError("fresh output with exact original Track1 basename required")
    _private_dir(output.parent)
    if output.parent.resolve() == directory.resolve():
        raise ValueError("assembled Track1 must be stored outside the ZIP folder")
    name = "." + secrets.token_hex(16) + ".partial"
    temp = output.parent / name
    whole = hashlib.sha256()
    bytes_out = 0
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as destination:
            for i, entry in enumerate(doc["parts"]):
                zpath = directory / entry["archive"]
                _private_path(zpath)
                state = _file_digest(zpath)
                if state[0] != entry["archive_bytes"] or state[1] != entry["archive_sha256"]:
                    raise ValueError("private ZIP bytes changed since splitting")
                with zipfile.ZipFile(zpath, "r", allowZip64=True) as zipped:
                    infos = zipped.infolist()
                    if len(infos) != 1:
                        raise ValueError("ZIP must have exactly one raw chunk")
                    info = infos[0]
                    if (info.filename != entry["member"] or
                            info.compress_type != zipfile.ZIP_STORED or
                            info.file_size != entry["member_bytes"] or
                            info.flag_bits & 1):
                        raise ValueError("invalid ZIP member")
                    part_sha = hashlib.sha256()
                    count = 0
                    with zipped.open(info, "r") as member:
                        while True:
                            block = member.read(IO_BLOCK)
                            if not block:
                                break
                            destination.write(block)
                            whole.update(block)
                            part_sha.update(block)
                            count += len(block)
                            if count > entry["member_bytes"]:
                                raise ValueError("ZIP part overlong")
                    if (count != entry["member_bytes"] or
                            part_sha.hexdigest() != entry["member_sha256"]):
                        raise ValueError("corrupted or reordered ZIP member")
                if state != _file_digest(zpath):
                    raise ValueError("archive mutated while reconstructing")
                bytes_out += count
            destination.flush()
            os.fsync(destination.fileno())
            if (bytes_out != size_pin or whole.hexdigest() != sha_pin or
                    os.fstat(destination.fileno()).st_size != size_pin):
                raise ValueError("full assembled Track1 differs from Stage02")
            os.fchmod(destination.fileno(), 0o400)
        os.link(temp, output)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
    return {
        "kind": "STAGE97_PRIVATE_REASSEMBLY_ONLY",
        "full_stage02_track1_sha256_verified": True,
        "reassembled_bytes": bytes_out,
        "independently_verified_archive_count": len(doc["parts"]),
        "original_game_boot_verified": False,
        "source_loader_verified": False,
        "public_media_upload_performed": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="operation", required=True)
    split = sub.add_parser("split")
    split.add_argument("--track1", type=Path, required=True)
    split.add_argument("--parts-dir", type=Path, required=True)
    split.add_argument("--chunk-mib", type=int, default=128)
    join = sub.add_parser("join")
    join.add_argument("--parts-dir", type=Path, required=True)
    join.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        if a.operation == "split":
            report = split_private_track1(
                a.track1, a.parts_dir, chunk_bytes=a.chunk_mib * 1024 * 1024
            )
        else:
            report = join_private_track1(a.parts_dir, a.output)
    except (OSError, ValueError, TypeError, zipfile.BadZipFile,
            zipfile.LargeZipFile, UnicodeError):
        print("STAGE97_PRIVATE_TRACK1_SPLIT_JOIN_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
