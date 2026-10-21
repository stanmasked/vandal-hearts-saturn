#!/usr/bin/env python3
"""Stage93: local-only complete Saturn disc source/ISO boot-readiness preflight.

Nothing here starts Yabause, reads copyrighted assets into public CI,
or asserts that the original game has actually booted.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

from tools.saturn_iso import SaturnISO
from tools.saturn_private_capture_session import PINNED, _fingerprint, _not_in_checkout
from tools.saturn_private_split_cue_preflight import audit_private_cue

# Stage02 *previously measured* private English v1.1 disc metadata, rather
# than guesses made from the public synthetic Stage89 two-sector fixture.
STAGE02_ISO = {
    "boot_product_code": "T-9526G",
    "volume_id": "VANDAL_HEARTS",
    "sectors": 264352,
    "declared_iso_sectors": 264352,
    "files": 848,
    "directories": 2,
    "extension_counts": {
        "MAP": 74, "PRG": 157, "DAT": 293, "BIN": 283,
        "AVI": 18, "PCM": 8, "TEX": 8, "TXT": 3,
        "CRT": 1, "EMR": 1, "<NONE>": 2,
    },
}
# Their presence was observed in Stage02's private metadata-only inventory.
STAGE02_RESOURCE_NAMES = frozenset(("MAP_1_1C.BIN", "BATL1PRG.BIN"))


def _source_paths(cue: Path, track1: Path, track2: Path) -> dict[str, Path]:
    paths = {"cue": cue, "track1": track1, "track2": track2}
    if any(not isinstance(p, Path) or not p.is_absolute() for p in paths.values()):
        raise ValueError("all three private source paths must be absolute")
    for path in paths.values():
        _not_in_checkout(path)
    if len({str(p.resolve()) for p in paths.values()}) != 3:
        raise ValueError("disc source paths are duplicated")
    return paths


def _pinned_snapshot(paths: dict[str, Path]) -> dict:
    result = {}
    for role, path in paths.items():
        size, sha, identity = _fingerprint(path)
        expected_size, expected_sha = PINNED[role]
        if ((expected_size is not None and size != expected_size) or
                sha != expected_sha):
            raise ValueError("private source does not match Stage02")
        result[role] = (size, sha, identity)
    return result


def audit_boot_readiness(
    cue: Path,
    track1: Path,
    track2: Path,
    *,
    expected_iso: dict | None = None,
    expected_resources: frozenset[str] | None = None,
) -> dict:
    """Return metadata-only receipt; refuse any incomplete or mutated disc.

    No original sector/file payload, private absolute path, SHA-256, Drive ID,
    CUE catalog number or ISO directory filename is emitted.
    """
    paths = _source_paths(cue, track1, track2)
    before = _pinned_snapshot(paths)
    expected_iso = STAGE02_ISO if expected_iso is None else expected_iso
    expected_resources = (
        STAGE02_RESOURCE_NAMES if expected_resources is None else expected_resources
    )
    if not isinstance(expected_iso, dict) or not isinstance(expected_resources, frozenset):
        raise ValueError("invalid independent metadata expectations")
    try:
        # Stage90 rejects a missing Track1 or a metadata-size-only substitute.
        cue_result = audit_private_cue(cue, track2, track1=track1)
        if (not cue_result["local_media_ready_for_capture"] or
                cue_result["blockers"] or
                not cue_result["data_track_stage02_sha256_verified"]):
            raise ValueError("full private Track1 verification required")

        report = SaturnISO(track1).inspect(include_files=True)
        for key, value in expected_iso.items():
            if report.get(key) != value:
                raise ValueError("private Saturn ISO9660 metadata changed")
        files = report.get("file_entries")
        if not isinstance(files, list):
            raise ValueError("missing ISO file extent inventory")
        names = {str(entry["name"]).upper().rsplit("/", 1)[-1] for entry in files}
        if not expected_resources.issubset(names):
            raise ValueError("Stage02 resource filenames absent from private ISO")
        for entry in files:
            lba, size = entry["lba"], entry["bytes"]
            if (type(lba) is not int or type(size) is not int or
                    lba < 0 or size < 0 or
                    lba + (size + 2047) // 2048 > report["sectors"]):
                raise ValueError("bad ISO9660 extent")
    finally:
        # Crucial after-check runs even if ISO metadata parsing fails.
        after = _pinned_snapshot(paths)
        if before != after:
            raise ValueError("private disc changed during complete preflight")
    return {
        "schema_version": 1,
        "kind": "STAGE93_PRIVATE_SATURN_SOURCE_BOOT_PREFLIGHT_ONLY",
        "stage02_track1_sha256_verified_before_and_after": True,
        "stage02_track2_sha256_verified_before_and_after": True,
        "stage02_cue_sha256_verified_before_and_after": True,
        "iso9660_boot_header_and_product_code_verified": True,
        "iso9660_stage02_inventory_counts_verified": True,
        "iso9660_file_extents_within_track1": True,
        "stage02_resource_candidate_names_present": True,
        "cue_two_track_layout_verified": True,
        "source_snapshot_identity_stable": True,
        "logical_data_sector_count": report["sectors"],
        "iso_file_count": report["files"],
        "iso_directory_count": report["directories"],
        "boot_ready_for_private_operator_validation": True,
        "actual_yabause_executable_verified": False,
        "original_game_boot_observed": False,
        "real_first_battle_scene_observed": False,
        "frame_synchronized_fad_read_verified": False,
        "source_japanese_master_equivalence_verified": False,
        "copyrighted_content_exported": False,
    }


def _write_receipt(path: Path, result: dict) -> None:
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ValueError("receipt must be a fresh private absolute file")
    _not_in_checkout(path)
    parent = path.parent
    if (parent.is_symlink() or not parent.is_dir() or
            stat.S_IMODE(parent.stat().st_mode) & 0o077):
        raise ValueError("receipt must be in a protected private directory")
    with path.open("x", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cue", type=Path, required=True)
    parser.add_argument("--track1", type=Path, required=True)
    parser.add_argument("--track2", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    try:
        result = audit_boot_readiness(args.cue, args.track1, args.track2)
        if args.receipt is not None:
            _write_receipt(args.receipt, result)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        print("STAGE93_PRIVATE_DISC_BOOT_PREFLIGHT_REJECTED", file=sys.stderr)
        return 1
    # No filesystem paths, original hashes, asset names or sector bytes.
    print("STAGE93_PRIVATE_DISC_SOURCE_INTEGRITY_PASS "
          "original_game_boot_observed=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
