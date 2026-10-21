#!/usr/bin/env python3
"""Stage90: privacy-safe audit of local English-v1.1 Saturn split CUE layout.

The CUE and each accessible track are checked against the previously
established Stage02 private SHA-256/size pins. A Drive metadata size alone
never substitutes for reading and hashing local Track1.
No sector bytes, filenames, source paths or digests are emitted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from tools.saturn_private_capture_session import PINNED, _fingerprint

CATALOG = re.compile(r"CATALOG [0-9]{13}\Z")
FILE = re.compile(r'FILE "([^"/\\]+)" BINARY\Z')
TRACK_DATA = "TRACK 01 MODE1/2352"
TRACK_AUDIO = "TRACK 02 AUDIO"
INDEX_DATA = "INDEX 01 00:00:00"
INDEX_AUDIO00 = "INDEX 00 00:00:00"
INDEX_AUDIO01 = "INDEX 01 00:02:00"
FRAMES_PER_SECOND = 75
RAW_SECTOR = 2352
MAX_CUE_BYTES = 8192


def _basename(name: str) -> str:
    if (not isinstance(name, str) or not name or
            name in {".", ".."} or ".." in name or
            "/" in name or "\\" in name):
        raise ValueError("invalid CUE filename")
    return name


def inspect_cue(cue_bytes: bytes, *, track1_bytes: int, track2_bytes: int) -> dict:
    if (not isinstance(cue_bytes, bytes) or
            len(cue_bytes) == 0 or len(cue_bytes) > MAX_CUE_BYTES):
        raise ValueError("invalid CUE bytes or length")
    try:
        source = cue_bytes.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("nonascii CUE") from error
    # This exact English-v1.1 layout is deliberately narrower than general
    # CUE grammar. Unknown commands or extra tracks cannot be guessed.
    lines = [line.strip() for line in source.splitlines()]
    if len(lines) != 8 or not CATALOG.fullmatch(lines[0]):
        raise ValueError("not an eight-line two-track Saturn CUE")
    first = FILE.fullmatch(lines[1])
    second = FILE.fullmatch(lines[4])
    if not first or not second:
        raise ValueError("not exactly two binary FILE declarations")
    a, b = _basename(first.group(1)), _basename(second.group(1))
    if a == b or (
        lines[2] != TRACK_DATA or lines[3] != INDEX_DATA or
        lines[5] != TRACK_AUDIO or lines[6] != INDEX_AUDIO00 or
        lines[7] != INDEX_AUDIO01
    ):
        raise ValueError("unexpected track order, type or indices")
    if (type(track1_bytes) is not int or type(track2_bytes) is not int or
            track1_bytes <= 0 or track2_bytes <= RAW_SECTOR * 150 or
            track1_bytes % RAW_SECTOR or track2_bytes % RAW_SECTOR):
        raise ValueError("invalid RAW/2352 track sizes")
    data_frames = track1_bytes // RAW_SECTOR
    audio_file_frames = track2_bytes // RAW_SECTOR
    pregap_frames = 2 * 60 * FRAMES_PER_SECOND
    first_audio_fad = 150 + data_frames + pregap_frames
    first_data_fad = 150
    end_data_fad = first_audio_fad - pregap_frames - 1
    last_audio_fad = first_audio_fad + audio_file_frames - pregap_frames - 1
    if data_frames > 0x7FFFFFFF // RAW_SECTOR or last_audio_fad >= 0xFFFFFFFF:
        raise ValueError("track address overflow")
    return {
        "track1_filename": a,
        "track2_filename": b,
        "data_sector_count": data_frames,
        "audio_file_sector_count": audio_file_frames,
        "audio_pregap_sectors": pregap_frames,
        "active_audio_sector_count": audio_file_frames - pregap_frames,
        "data_fad_start": first_data_fad,
        "data_fad_end": end_data_fad,
        "audio_index01_fad": first_audio_fad,
        "audio_fad_end": last_audio_fad,
        "leadout_fad": last_audio_fad + 1,
    }


def _verify_local_file(path: Path, role: str) -> None:
    if not path.is_absolute():
        raise ValueError("absolute local source path required")
    size, digest, _ = _fingerprint(path)
    expected_size, expected_digest = PINNED[role]
    if (expected_size is not None and size != expected_size) or digest != expected_digest:
        raise ValueError("local source does not match Stage02 pin")


def audit_private_cue(
    cue: Path,
    track2: Path,
    *,
    track1: Path | None = None,
    track1_metadata_name: str | None = None,
    track1_metadata_size: int | None = None,
) -> dict:
    _verify_local_file(cue, "cue")
    _verify_local_file(track2, "track2")
    if track1 is not None:
        _verify_local_file(track1, "track1")
    elif (track1_metadata_name is None or
          track1_metadata_size != PINNED["track1"][0]):
        raise ValueError("Track1 lacks usable pinned-size metadata")
    info = inspect_cue(
        cue.read_bytes(),
        track1_bytes=PINNED["track1"][0],
        track2_bytes=PINNED["track2"][0],
    )
    track1_expected_name = (
        track1.name if track1 is not None else
        _basename(track1_metadata_name)
    )
    if info["track1_filename"] != track1_expected_name or (
            info["track2_filename"] != track2.name):
        raise ValueError("CUE filename does not match declared local/Drive source")
    present = track1 is not None
    return {
        "schema_version": 1,
        "kind": "PRIVATE_TWO_FILE_SATURN_CUE_PREFLIGHT_ONLY",
        "cue_stage02_sha256_verified": True,
        "audio_track_stage02_sha256_verified": True,
        "data_track_stage02_sha256_verified": present,
        "data_track_declared_size_matches_stage02": True,
        "track1_sector_count": info["data_sector_count"],
        "track2_pregap_sector_count": info["audio_pregap_sectors"],
        "track2_active_audio_sectors": info["active_audio_sector_count"],
        "track1_fad_first": info["data_fad_start"],
        "track1_fad_last": info["data_fad_end"],
        "track2_index01_fad": info["audio_index01_fad"],
        "track2_fad_last": info["audio_fad_end"],
        "cue_parser_layout_compatible_with_stage89": True,
        "local_media_ready_for_capture": present,
        "blockers": [] if present else ["TRACK1_CONTENT_NOT_LOCALLY_HASH_VERIFIED"],
        "original_game_boot_verified": False,
        "first_battle_scene_verified": False,
        "resource_loader_verified": False,
        "japanese_master_verified": False,
        "private_sector_data_exported": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cue", required=True, type=Path)
    ap.add_argument("--track2", required=True, type=Path)
    ap.add_argument("--track1", type=Path)
    ap.add_argument("--track1-metadata-name")
    ap.add_argument("--track1-metadata-size", type=int)
    args = ap.parse_args()
    try:
        result = audit_private_cue(
            args.cue, args.track2, track1=args.track1,
            track1_metadata_name=args.track1_metadata_name,
            track1_metadata_size=args.track1_metadata_size,
        )
    except (OSError, ValueError, UnicodeError, TypeError):
        print("STAGE90_PRIVATE_CUE_PREFLIGHT_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["local_media_ready_for_capture"] else 2


if __name__ == "__main__":
    sys.exit(main())
