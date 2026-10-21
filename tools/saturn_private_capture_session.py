#!/usr/bin/env python3
"""Stage86: private-only, pinned Saturn source integrity and gated FAD capture.

Runs a locally available instrumented Yabause command without copying, moving,
extracting or publishing any source media. The caller manually operates the
capture window. A passing receipt is NOT proof that the first battle ran.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import stat
import subprocess
import sys

from tools.saturn_yabause_fad_log import MAX_LOG_BYTES, parse_fad_log

# Pinned against the read-only Stage02 private audit, NOT a Japanese master.
PINNED = {
    "track1": (621755904, "d9855ae466725056dbb1f42c852cb02c4c35f223b4b6f9d481c9605ff786fe45"),
    "track2": (2102688, "245f3f846b483bb2028f2ce86277b4fea5c98f2f5412450f97b6e3b198ac4915"),
    "cue": (None, "a97fcec5d7168a91c2d79f87053b75b7e1dc124fd48bb4fae9d12fd114d6112c"),
}
PHASES = {"menu_control", "first_battle_entry"}
LOG_FILE = "fad.vhcdlog"
GATE_FILE = "capture.vhgate"
RECEIPT_FILE = "private-receipt.json"
EXACT_LOG = re.compile(rb"(?:VHCD_FAD (?:0|[1-9][0-9]{0,8})\n){1,10000}\Z")


def _not_in_checkout(path: Path) -> None:
    # Resolve parent aliases as well: paths entering a checkout through a
    # symlinked ancestor must not bypass the local-only output boundary.
    resolved = path.resolve()
    for candidate in (path, resolved):
        for parent in (candidate, *candidate.parents):
            if (parent / ".git").exists():
                raise ValueError("private source or output inside a git checkout")


def _regular_no_link(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("source/output must be a regular unlinked file")


def _fingerprint(path: Path) -> tuple[int, str, tuple[int, ...]]:
    _regular_no_link(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        with os.fdopen(fd, "rb", closefd=False) as stream:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ValueError("media changed during open")
            h = hashlib.sha256()
            count = 0
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                count += len(block)
                h.update(block)
            after = os.fstat(fd)
            identity = lambda st: (
                st.st_dev, st.st_ino, st.st_size,
                st.st_mtime_ns, st.st_ctime_ns,
            )
            if identity(before) != identity(after) or count != after.st_size:
                raise ValueError("media mutated while hashing")
            return count, h.hexdigest(), identity(after)
    finally:
        os.close(fd)


def inspect_sources(manifest: dict, *, pins=PINNED) -> dict:
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version", "product_code", "release_kind", "files"
    } or manifest["schema_version"] != 1 or manifest["product_code"] != "T-9526G" \
            or manifest["release_kind"] != "translation_patched":
        raise ValueError("unexpected private source manifest")
    sources = manifest["files"]
    if not isinstance(sources, dict) or set(sources) != set(pins):
        raise ValueError("expected all three privately held source files")
    snapshots = {}
    seen = set()
    for role in sorted(pins):
        value = sources[role]
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise ValueError("manifest paths must be absolute")
        path = Path(value)
        _not_in_checkout(path)
        if path in seen:
            raise ValueError("media path reused")
        seen.add(path)
        size, digest, identity = _fingerprint(path)
        expected_size, expected_digest = pins[role]
        if (expected_size is not None and size != expected_size) or digest != expected_digest:
            raise ValueError("media differs from Stage02 pinned source")
        snapshots[role] = (str(path), size, digest, identity)
    return snapshots


def inspect_log(path: Path) -> int:
    _regular_no_link(path)
    if path.stat().st_size > MAX_LOG_BYTES:
        raise ValueError("oversized CD FAD log")
    raw = path.read_bytes()
    if not EXACT_LOG.fullmatch(raw):
        raise ValueError("noncanonical or nonnumeric CD trace")
    return len(parse_fad_log(raw.decode("ascii")))


def _private_empty_dir(directory: Path) -> None:
    if not directory.is_absolute() or directory.is_symlink() or not directory.is_dir():
        raise ValueError("private workspace must exist and be absolute")
    _not_in_checkout(directory)
    if stat.S_IMODE(directory.stat().st_mode) & 0o077:
        raise ValueError("private workspace requires chmod 700")
    if any(directory.iterdir()):
        raise ValueError("new empty capture workspace required")


def _run_bounded(command: list[str], *, private_dir: Path, seconds: int) -> int:
    if not command or not Path(command[0]).is_absolute():
        raise ValueError("absolute emulator executable required")
    if not (1 <= seconds <= 18000):
        raise ValueError("invalid timeout")
    env = os.environ.copy()
    env["VH_SATURN_CAPTURE_GATE"] = str(private_dir / GATE_FILE)
    env["VH_SATURN_FAD_LOG"] = str(private_dir / LOG_FILE)
    process = subprocess.Popen(
        command, cwd=private_dir, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        return process.wait(timeout=seconds)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise ValueError("local emulator process timed out") from exc


def capture_private(
    manifest: dict, private_dir: Path, phase: str, command: list[str],
    *, seconds=1800, pins=PINNED,
) -> dict:
    if phase not in PHASES:
        raise ValueError("phase must be a defined capture window")
    _private_empty_dir(private_dir)
    start = inspect_sources(manifest, pins=pins)
    try:
        status = _run_bounded(command, private_dir=private_dir, seconds=seconds)
    finally:
        # Always recheck media after a launch attempt, even on process failure.
        end = inspect_sources(manifest, pins=pins)
        if end != start:
            raise ValueError("source identity changed during session")
    if status != 0:
        raise ValueError("local emulator returned a nonzero status")
    if (private_dir / GATE_FILE).exists() or (private_dir / GATE_FILE).is_symlink():
        raise ValueError("manual capture gate was not closed")
    if {p.name for p in private_dir.iterdir()} != {LOG_FILE}:
        raise ValueError("unexpected local capture outputs")
    events = inspect_log(private_dir / LOG_FILE)
    receipt = {
        "schema_version": 1,
        "kind": "PRIVATE_SATURN_FAD_CAPTURE_INTEGRITY_ONLY",
        "session_id": secrets.token_hex(16),
        "phase_operator_declared": phase,
        "pinned_english_v1_1_track1_track2_cue_match": True,
        "pinned_files_unchanged_after_run": True,
        "numeric_fad_events": events,
        "manual_gate_closed_at_exit": True,
        "original_game_execution_verified": False,
        "scene_frame_synchronized_verified": False,
        "session_independence_verified": False,
        "first_battle_loader_verified": False,
        "japanese_master_identity_verified": False,
        "media_bytes_exported": False,
    }
    output = private_dir / RECEIPT_FILE
    with output.open("x", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    return receipt


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--private-dir", type=Path, required=True)
    p.add_argument("--phase", choices=sorted(PHASES), required=True)
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("command", nargs=argparse.REMAINDER,
                   help="-- followed by absolute executable and its arguments")
    a = p.parse_args()
    try:
        if not a.manifest.is_absolute() or not a.command or a.command[0] != "--":
            raise ValueError("manifest must be private, command must follow --")
        _not_in_checkout(a.manifest)
        _regular_no_link(a.manifest)
        manifest = json.loads(a.manifest.read_text(encoding="utf-8"))
        capture_private(manifest, a.private_dir, a.phase, a.command[1:],
                        seconds=a.timeout)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError,
            subprocess.SubprocessError):
        print("STAGE86_PRIVATE_CAPTURE_REJECTED", file=sys.stderr)
        return 1
    print("STAGE86_PRIVATE_CAPTURE_INTEGRITY_PASS scene_authenticated=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
