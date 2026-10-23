#!/usr/bin/env python3
"""Stage129: re-audit both Stage124 runs FROM a pinned private TAR.GZIP.

Extracts only allowlisted capture filenames to short-lived owner-only scratch;
never extracts arbitrary archive paths, original BIN/CUE or public artifacts.
Public tests use entirely invented capture outputs.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile
import tempfile

from tools.saturn_private_capture_archive_gate import (
    SIDECARS, _private_fingerprint, verify_private_stage124_archive,
)
from tools.saturn_private_prologue_continue_ninth_c import (
    CHECKPOINTS, NONA_EVENTS, OCTA_EVENTS_108,
    audit_private_prologue_continue_ninth_c,
)

ALLOWED = frozenset(f"frame-{frame}.png" for frame in CHECKPOINTS) | SIDECARS


def audit_archived_stage124_pair(archive: Path, *, expected_size: int,
                                expected_sha256: str) -> dict:
    initial = _private_fingerprint(archive)
    shape = verify_private_stage124_archive(
        archive, expected_size=expected_size, expected_sha256=expected_sha256)
    if shape.get("checkpoint_pngs") != 1800:
        raise ValueError("Stage124 structural preflight incomplete")

    members: dict[PurePosixPath, dict[str, tarfile.TarInfo]] = {}
    try:
        with tarfile.open(archive, "r:gz") as tar:
            for entry in tar:
                if not entry.isfile():
                    continue
                name = PurePosixPath(entry.name)
                if name.name in ALLOWED:
                    cohort = members.setdefault(name.parent, {})
                    if name.name in cohort:
                        raise ValueError("duplicate archive capture filename")
                    cohort[name.name] = entry
            if len(members) != 2 or any(set(group) != ALLOWED for group in members.values()):
                raise ValueError("Stage124 archive cohorts incomplete")
            with tempfile.TemporaryDirectory(prefix="vh-saturn-stage129-private-") as private:
                base = Path(private)
                assigned: dict[str, Path] = {}
                for group in members.values():
                    event = tar.extractfile(group["pad-events.txt"])
                    if event is None:
                        raise ValueError("Stage124 archived PAD receipt unavailable")
                    with event:
                        pad = event.read(2049)
                    role = ("control" if pad == OCTA_EVENTS_108 else
                            "enabled" if pad == NONA_EVENTS else None)
                    if role is None or role in assigned:
                        raise ValueError("Stage124 archived PAD receipt invalid or duplicate")
                    dest = base / role
                    dest.mkdir(mode=0o700)
                    assigned[role] = dest
                    for filename, member in group.items():
                        source = tar.extractfile(member)
                        if source is None:
                            raise ValueError("Stage124 archive capture member unreadable")
                        # Filename is an internal fixed allowlist, not archive path.
                        out = dest / filename
                        descriptor = os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                        with source, os.fdopen(descriptor, "wb") as sink:
                            shutil.copyfileobj(source, sink, length=1024*1024)
                        if out.stat().st_size != member.size:
                            raise ValueError("Stage124 extracted capture incomplete")
                if set(assigned) != {"control", "enabled"}:
                    raise ValueError("Stage124 control/enabled cohorts missing")
                audited = audit_private_prologue_continue_ninth_c(
                    assigned["control"], assigned["enabled"])
                if (audited.get("checkpoint_png_count_per_process") != 900
                        or audited.get("pre_ninth_checkpoint_equal_count") != 799
                        or audited.get("first_battle_or_player_control_verified") is not False):
                    raise ValueError("Stage124 paired semantic audit incomplete")
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise ValueError("Stage124 archive semantic audit could not complete") from exc

    if _private_fingerprint(archive) != initial:
        raise ValueError("Stage124 archive mutated during semantic audit")
    return {
        "stage": 129,
        "archive_matches_supplied_fingerprint": True,
        "stage124_paired_capture_semantics_verified_in_archive": True,
        "pre_ninth_checkpoints_equal": 799,
        "checkpoint_pngs": 1800,
        "historical_archive_provenance_authenticated": False,
        "owner_only_drive_readback_authenticated": False,
        "original_gameplay_or_battle_verified": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--expected-size", type=int, required=True)
    p.add_argument("--expected-sha256", required=True)
    a = p.parse_args()
    try:
        result = audit_archived_stage124_pair(
            a.archive, expected_size=a.expected_size, expected_sha256=a.expected_sha256)
    except (OSError, ValueError, TypeError, tarfile.TarError):
        print("STAGE129_PRIVATE_PAIR_SEMANTIC_AUDIT_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
