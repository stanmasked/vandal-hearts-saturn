#!/usr/bin/env python3
"""Stage126: package a *new* Stage124-style private capture pair, without any media.

A newly generated archive is NOT the missing historical Stage124 capture and
does not prove original-disc runtime or Google Drive durability. The two inputs
must have independently passed the private Stage124 paired-run audit.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path
import re
import stat
import sys
import tarfile

from tools.saturn_private_capture_archive_gate import (
    ROOT, SIDECARS, MAX_MEMBER, MAX_TOTAL, _private_fingerprint,
    verify_private_stage124_archive,
)

FRAME = re.compile(r"frame-(\d+)\.png\Z")
MAX_FILES = 1816


def _outside_checkout(path: Path) -> None:
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("private absolute nonsymlinked path required")
    resolved = path.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError("private file path must be outside public Git checkout")


def _capture_files(folder: Path, checkpoints: int) -> list[tuple[str, Path, tuple[int, ...]]]:
    _outside_checkout(folder)
    if not folder.is_dir():
        raise ValueError("private capture directory unavailable")
    names = {f"frame-{i}.png" for i in range(120, checkpoints * 120 + 1, 120)}
    names.update(SIDECARS)
    if {p.name for p in folder.iterdir()} != names:
        raise ValueError("private capture file set incomplete or unexpected")
    found = []
    for name in sorted(names):
        source = folder / name
        info = source.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_MEMBER:
            raise ValueError("unsafe, linked or oversized capture source")
        identity = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        found.append((name, source, identity))
    return found


def package_stage124_style_pair(control: Path, enabled: Path, archive: Path,
                               *, checkpoints: int = 900) -> dict:
    """Create a fresh, private archive from two immutable audited raw cohorts."""
    if type(checkpoints) is not int or not 1 <= checkpoints <= 900:
        raise ValueError("invalid checkpoint count")
    for p in (control, enabled, archive):
        _outside_checkout(p)
    a, b, out = control.resolve(), enabled.resolve(), archive.resolve()
    if a == b or a in b.parents or b in a.parents:
        raise ValueError("capture cohort paths overlap")
    if any(out == x or x in out.parents or out in x.parents for x in (a, b)):
        raise ValueError("archive overlaps source directory")
    if archive.exists() or archive.is_symlink():
        raise ValueError("archive destination must not preexist")
    if not archive.parent.is_dir():
        raise ValueError("private output parent directory unavailable")

    cohort = {"control": _capture_files(control, checkpoints),
              "enabled": _capture_files(enabled, checkpoints)}
    if sum(len(v) for v in cohort.values()) != 2 * (checkpoints + len(SIDECARS)):
        raise ValueError("incomplete input file inventory")
    total = sum(fingerprint[2] for files in cohort.values() for _, _, fingerprint in files)
    if total > MAX_TOTAL:
        raise ValueError("private archive exceeds safe expanded data limit")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(archive, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as sink:
            with gzip.GzipFile(filename="", fileobj=sink, mode="wb", mtime=0) as zipstream:
                with tarfile.open(fileobj=zipstream, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                    for cohort_name, files in cohort.items():
                        for name, source, identity in files:
                            f = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                            with os.fdopen(f, "rb") as src:
                                stat_before = os.fstat(src.fileno())
                                actual = (stat_before.st_dev, stat_before.st_ino, stat_before.st_size,
                                          stat_before.st_mtime_ns, stat_before.st_ctime_ns)
                                if actual != identity or not stat.S_ISREG(stat_before.st_mode):
                                    raise ValueError("capture source changed before packaging")
                                item = tarfile.TarInfo(f"stage124-recapture/{cohort_name}/{name}")
                                item.size = stat_before.st_size
                                item.mode = 0o600
                                item.mtime = 0
                                item.uid = item.gid = 0
                                item.uname = item.gname = ""
                                tar.addfile(item, src)
                                stat_after = os.fstat(src.fileno())
                                if (stat_after.st_dev, stat_after.st_ino, stat_after.st_size,
                                    stat_after.st_mtime_ns, stat_after.st_ctime_ns) != identity:
                                    raise ValueError("capture source mutated while archiving")
            sink.flush()
            os.fsync(sink.fileno())
        nbytes, digest, _ = _private_fingerprint(archive)
        report = verify_private_stage124_archive(archive, expected_size=nbytes,
                                                 expected_sha256=digest, checkpoints=checkpoints)
        report["new_private_archive_requires_authenticated_drive_readback"] = True
        report["historical_stage124_archive_recovered"] = False
        return report
    except BaseException:
        # Only remove this new incomplete output; NEVER delete or mutate raw captures.
        archive.unlink(missing_ok=True)
        raise


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("control", "enabled", "archive"):
        p.add_argument("--" + key, type=Path, required=True)
    args = p.parse_args()
    try:
        result = package_stage124_style_pair(args.control, args.enabled, args.archive)
    except (OSError, ValueError, tarfile.TarError):
        print("STAGE126_PRIVATE_PACKAGING_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
