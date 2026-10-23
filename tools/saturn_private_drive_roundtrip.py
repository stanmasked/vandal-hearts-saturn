#!/usr/bin/env python3
"""Stage127: privately transfer and read back an independently pinned capture.

This tool cannot establish Google Drive ownership or create a Stage125 receipt.
rclone must be configured for the owner's private Drive OUTSIDE public Git.
Public CI runs exclusively with a mocked transfer, never with real credentials.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

from tools.saturn_private_capture_archive_gate import (
    ROOT, SHA256, _private_fingerprint, verify_private_stage124_archive,
)

REMOTE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}:.{1,512}\Z")


def _private_path(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("private absolute non-symlinked file path required")
    real = path.resolve()
    if real == ROOT or ROOT in real.parents:
        raise ValueError("private data must remain outside the public checkout")
    return real


def _private_remote(remote: str) -> None:
    if not isinstance(remote, str) or not REMOTE.fullmatch(remote):
        raise ValueError("private rclone remote:object path required")
    # Remote destination is an exact file path, not a root, command or URL.
    _, relative = remote.split(":", 1)
    if (relative.startswith(("/", "\\")) or relative.endswith(("/", "\\"))
            or any(part in ("", ".", "..") for part in relative.split("/"))
            or "\\" in relative or any(ord(ch) < 32 for ch in remote)):
        raise ValueError("unsafe remote object path")


def _transfer(rclone: str, source: str, destination: str, *, ignore_existing: bool) -> None:
    cmd = [rclone, "copyto"]
    if ignore_existing:
        cmd.append("--ignore-existing")
    cmd.extend([source, destination])
    try:
        p = subprocess.run(cmd, check=False, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=3600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("private transfer command could not complete") from exc
    if p.returncode:
        # Never echo provider errors: they may contain private object paths.
        raise ValueError("private transfer command failed")


def private_archive_roundtrip(archive: Path, destination: str, readback: Path,
                              *, expected_size: int, expected_sha256: str,
                              rclone: str = "rclone") -> dict:
    src, out = _private_path(archive), _private_path(readback)
    _private_remote(destination)
    if src == out or src in out.parents or out in src.parents:
        raise ValueError("readback must be separate from source archive")
    if readback.exists() or readback.is_symlink():
        raise ValueError("readback destination must not already exist")
    if (not readback.parent.is_dir() or readback.parent.is_symlink()
            or stat.S_IMODE(readback.parent.stat().st_mode) & 0o077):
        raise ValueError("readback parent must be an existing private directory")
    if not isinstance(rclone, str) or not rclone.strip():
        raise ValueError("rclone executable unavailable")
    program = shutil.which(rclone)
    if program is None:
        raise ValueError("rclone executable unavailable")

    # Do not upload arbitrary files or trust a matching receipt; read original
    # bytes locally and inspect the full Stage124-shaped archive first.
    fingerprint = _private_fingerprint(src)
    verify_private_stage124_archive(src, expected_size=expected_size,
                                    expected_sha256=expected_sha256)
    if _private_fingerprint(src) != fingerprint:
        raise ValueError("private source mutated before transfer")

    # Reserve the destination O_EXCL in a private directory to prevent a
    # pre-existing symlink or old download being overwritten.
    fd = os.open(readback, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    os.close(fd)
    try:
        _transfer(program, str(src), destination, ignore_existing=True)
        _transfer(program, destination, str(out), ignore_existing=False)
        if _private_fingerprint(src) != fingerprint:
            raise ValueError("private source mutated during transfer")
        downloaded = _private_fingerprint(out)
        if downloaded[0] != fingerprint[0] or downloaded[1] != fingerprint[1]:
            raise ValueError("private remote readback checksum mismatch")
        verify_private_stage124_archive(out, expected_size=expected_size,
                                        expected_sha256=expected_sha256)
        if _private_fingerprint(src) != fingerprint:
            raise ValueError("private source mutated during verification")
        return {
            "stage": 127,
            "configured_remote_roundtrip_verified": True,
            "readback_archive_structurally_verified": True,
            "original_source_preserved": True,
            "google_drive_owner_only_verified": False,
            "stage125_drive_receipt_issued": False,
            "historical_stage124_archive_recovered": False,
            "readback_bytes": downloaded[0],
        }
    except BaseException:
        # Remove only the newly reserved or incomplete readback. Preserve
        # source and any transferred remote object for investigation.
        readback.unlink(missing_ok=True)
        raise


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--remote-object", required=True)
    p.add_argument("--readback", type=Path, required=True)
    p.add_argument("--expected-size", type=int, required=True)
    p.add_argument("--expected-sha256", required=True)
    args = p.parse_args()
    try:
        result = private_archive_roundtrip(
            args.archive, args.remote_object, args.readback,
            expected_size=args.expected_size, expected_sha256=args.expected_sha256)
    except (ValueError, OSError, TypeError, subprocess.SubprocessError):
        print("STAGE127_PRIVATE_DRIVE_ROUNDTRIP_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
