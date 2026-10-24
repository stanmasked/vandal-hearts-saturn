"""Stage132: test private remote write/read/delete using INVENTED canary bytes.

Never use original BIN/CUE or captured PNGs for a connectivity probe.
Does not authenticate the remote as owner-only Google Drive.
"""
from __future__ import annotations
import os
from pathlib import Path, PurePosixPath
import secrets
import shutil
import subprocess
import tempfile

from tools.saturn_private_drive_roundtrip import _private_remote


def _command(executable: str, args: list[str]) -> None:
    try:
        result = subprocess.run(
            [executable] + args, check=False, timeout=120,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("private remote canary transfer unavailable") from exc
    if result.returncode:
        raise ValueError("private remote canary operation rejected")


def verify_private_remote_canary(destination: str, *, rclone: str = "rclone") -> dict:
    """Exercise actual configured remote permissions BEFORE private gameplay.

    Uses a unique random non-original object, deletes only that object after
    verification, and fails closed if cleanup cannot be confirmed.
    """
    _private_remote(destination)
    prefix, relative = destination.split(":", 1)
    parent = PurePosixPath(relative).parent
    if str(parent) == ".":
        raise ValueError("private remote requires a named parent directory")
    exe = shutil.which(rclone)
    if not exe:
        raise ValueError("private rclone executable unavailable")
    leaf = ".vh-saturn-stage132-canary-" + secrets.token_hex(12) + ".txt"
    remote_object = prefix + ":" + str(parent / leaf)
    invented = b"VH-SATURN-SYNTHETIC-REMOTE-PROBE\n" + secrets.token_bytes(32)
    uploaded = False
    failure = None
    verified = False
    with tempfile.TemporaryDirectory(prefix="vh-saturn-remote-probe-") as temp:
        source, readback = Path(temp) / "canary", Path(temp) / "readback"
        source.write_bytes(invented)
        os.chmod(source, 0o600)
        try:
            _command(exe, ["copyto", str(source), remote_object, "--immutable"])
            uploaded = True
            _command(exe, ["copyto", remote_object, str(readback)])
            if not readback.is_file() or readback.read_bytes() != invented:
                raise ValueError("private remote canary readback mismatch")
            verified = True
        except (OSError, ValueError) as exc:
            failure = exc
        finally:
            if uploaded:
                try:
                    _command(exe, ["deletefile", remote_object])
                except ValueError as cleanup:
                    raise ValueError("private remote canary cleanup not verified") from cleanup
    if failure is not None:
        raise ValueError("private remote canary not verified") from failure
    if not verified:
        raise ValueError("private remote canary not verified")
    return {
        "stage": 132,
        "synthetic_private_remote_write_read_delete_verified": True,
        "owner_only_google_drive_permissions_verified": False,
        "original_archive_uploaded": False,
        "stage125_receipt_issued": False,
    }
