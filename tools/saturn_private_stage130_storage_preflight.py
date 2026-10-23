"""Stage130: private destination preflight before costly Stage124 recapture.

This module does not open original disc files or connect to Google Drive.
"""
from __future__ import annotations
from pathlib import Path
import stat

from tools.saturn_private_drive_roundtrip import _private_path, _private_remote


def verify_new_capture_storage(control: Path, enabled: Path,
                               archive: Path, readback: Path,
                               destination: str) -> dict:
    """Fail before an original-game run when storage paths are unsafe."""
    for candidate in (control, enabled, archive, readback):
        _private_path(candidate)
    a, b = control.resolve(), enabled.resolve()
    if a == b or a.parent != b.parent:
        raise ValueError("separate sibling capture directories required")
    for folder in (control, enabled, archive.parent, readback.parent):
        _private_path(folder)
        if (not folder.is_dir() or folder.is_symlink()
                or stat.S_IMODE(folder.stat().st_mode) & 0o077):
            raise ValueError("owner-only private directory required")
    if any(control.iterdir()) or any(enabled.iterdir()):
        raise ValueError("new capture directories must be empty")
    if archive.exists() or archive.is_symlink() or readback.exists() or readback.is_symlink():
        raise ValueError("new archive and readback files must not preexist")
    paths = (a, b, archive.resolve(), readback.resolve())
    if len(set(paths)) != len(paths):
        raise ValueError("private output paths overlap")
    for output in (paths[2], paths[3]):
        if any(output in cohort.parents or cohort in output.parents for cohort in (a, b)):
            raise ValueError("private capture data paths overlap")
    _private_remote(destination)
    return {
        "new_capture_storage_preflight": True,
        "drive_upload_verified": False,
        "stage125_receipt_issued": False,
    }
