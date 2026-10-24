#!/usr/bin/env python3
"""Stage150: refuse ephemeral/CI storage for real Saturn private capture sessions.

This is a local host preflight only. It cannot prove that remote backup,
Google Drive independent readback, or power-loss durability has occurred.
"""
from __future__ import annotations

import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess

MIN_FREE_BYTES = 4 * 1024 * 1024 * 1024
PERSISTENT_LINUX_TYPES = frozenset({"ext2", "ext3", "ext4", "xfs", "btrfs",
                                    "zfs", "f2fs", "jfs", "reiserfs"})
PERSISTENT_MAC_TYPES = frozenset({"apfs", "hfs"})
CI_ENV_VARS = ("CI", "GITHUB_ACTIONS", "CIRCLECI", "GITLAB_CI",
               "BUILDKITE", "TF_BUILD", "BITBUCKET_BUILD_NUMBER")


def _forbid_symlink_components(path: Path) -> None:
    if not path.is_absolute():
        raise ValueError("Stage150 private host path must be absolute")
    cur = Path("/")
    for part in path.parts[1:]:
        cur = cur / part
        if cur.is_symlink():
            raise ValueError("Stage150 private source or capture ancestor contains symlink")


def _unescape_mountpoint(value: str) -> str:
    # Linux mountinfo octal escapes for space, tab, newline and backslash.
    # Refuse unknown escapes rather than guessing a mount location.
    result = []
    i = 0
    while i < len(value):
        if value[i] == "\\":
            code = value[i + 1:i + 4]
            if code not in ("040", "011", "012", "134"):
                raise ValueError("Stage150 Linux mountinfo has unknown escape")
            result.append(chr(int(code, 8)))
            i += 4
        else:
            result.append(value[i])
            i += 1
    return "".join(result)


def _parse_linux_mountinfo(data: str) -> tuple[tuple[Path, str], ...]:
    mounts: list[tuple[Path, str]] = []
    if not data or len(data) > 8 * 1024 * 1024:
        raise ValueError("Stage150 Linux mountinfo missing or oversized")
    for line in data.splitlines():
        if " - " not in line:
            raise ValueError("Stage150 Linux mountinfo line malformed")
        front, back = line.split(" - ", 1)
        fields, right = front.split(), back.split()
        if len(fields) < 5 or len(right) < 3:
            raise ValueError("Stage150 Linux mountinfo fields missing")
        mp = Path(_unescape_mountpoint(fields[4]))
        if not mp.is_absolute():
            raise ValueError("Stage150 Linux mountpoint is not absolute")
        mounts.append((mp, right[0].lower()))
    if not mounts:
        raise ValueError("Stage150 Linux mountinfo contains no filesystems")
    return tuple(mounts)


def _linux_type_for_path(path: Path, mounts: tuple[tuple[Path, str], ...]) -> str:
    resolved = path.resolve(strict=True)
    choices = [
        (len(mount.parts), fstype)
        for mount, fstype in mounts
        if resolved == mount or mount in resolved.parents
    ]
    if not choices:
        raise ValueError("Stage150 cannot resolve Linux mount for private files")
    return max(choices, key=lambda x: x[0])[1]


def _storage_type(path: Path, system: str) -> str:
    if system == "Linux":
        try:
            raw = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ValueError("Stage150 cannot read Linux mount provenance") from exc
        return _linux_type_for_path(path, _parse_linux_mountinfo(raw))
    if system == "Darwin":
        try:
            result = subprocess.run(
                ["/usr/bin/stat", "-f", "%T", str(path)],
                check=True, capture_output=True, text=True, timeout=10,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError("Stage150 cannot obtain macOS filesystem type") from exc
        if not result.stdout.strip() or "\n" in result.stdout.strip():
            raise ValueError("Stage150 unexpected macOS filesystem type")
        return result.stdout.strip().lower()
    raise ValueError("Stage150 only supports native Linux/macOS private capture hosts")


def assert_durable_private_workspace(root: Path, sources: tuple[Path, ...]) -> dict:
    """Block volatile storage, shared files, cloud/CI runners, and low disk space.

    This intentionally has NO environment override for unsafe storage types.
    Public CI tests must mock this function; public CI must never run real media.
    """
    if any(os.environ.get(k) for k in CI_ENV_VARS):
        raise ValueError("Stage150 original media is forbidden on CI-hosted runners")
    if not sources or not isinstance(root, Path):
        raise ValueError("Stage150 workspace and sources required")
    system = platform.system()
    allow = PERSISTENT_LINUX_TYPES if system == "Linux" else PERSISTENT_MAC_TYPES
    paths = (root,) + sources
    filesystems = []
    for path in paths:
        if not isinstance(path, Path) or not path.is_absolute():
            raise ValueError("Stage150 private workspace requires absolute paths")
        _forbid_symlink_components(path)
        info = path.lstat()
        if path == root:
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError("Stage150 capture root is not a directory")
        elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("Stage150 private input must be a unique regular file")
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError("Stage150 input or output permissions permit third-party access")
        fstype = _storage_type(path, system)
        if fstype not in allow:
            raise ValueError("Stage150 refuses volatile, network, or unverified filesystem")
        filesystems.append(fstype)
    if shutil.disk_usage(root).free < MIN_FREE_BYTES:
        raise ValueError("Stage150 persistent capture volume has insufficient free space")
    return {
        "native_host_class": system,
        "capture_and_source_volumes_accepted": True,
        "filesystem_types": sorted(set(filesystems)),
        "minimum_required_free_bytes": MIN_FREE_BYTES,
        "drive_upload_and_independent_readback_verified": False,
        "persistent_storage_survives_power_failure_independently_verified": False,
    }
