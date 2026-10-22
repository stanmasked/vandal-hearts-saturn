#!/usr/bin/env python3
"""Stage96: verify local screenshot file integrity alongside Stage95 FAD cohort.

Frames are not decoded or classified as actual Vandal Hearts scenes; the
frame counter and gate relationship are only self-declared metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zlib

from tools.saturn_private_capture_cohort import (
    _private_directory, _private_regular, _json_receipt,
    audit_four_capture_cohort,
)
from tools.saturn_private_capture_session import RECEIPT_FILE, LOG_FILE

MAX_PNG = 8 * 1024 * 1024
MAX_MANIFEST = 8192
HEX_SHA = re.compile(r"[0-9a-f]{64}\Z")
SESSION = re.compile(r"[0-9a-f]{32}\Z")
WITNESS_NAME = "frame-witness.json"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# Only PNG framing, dimensions and per-chunk CRC are examined, not gameplay.
ALLOWED_STAGES = ("before_gate", "after_gate")


def validate_png_file(raw: bytes) -> tuple[int, int]:
    if not raw.startswith(PNG_MAGIC) or len(raw) < 8 + 12 + 13:
        raise ValueError("not a PNG byte stream")
    pos, saw_ihdr, saw_plte, saw_idat, saw_iend = 8, False, False, False, False
    width = height = depth = color = 0
    while pos + 12 <= len(raw):
        n = struct.unpack(">I", raw[pos:pos+4])[0]
        kind = raw[pos+4:pos+8]
        end = pos + 12 + n
        if n > MAX_PNG or end > len(raw):
            raise ValueError("truncated or oversized PNG chunk")
        chunk = raw[pos+8:pos+8+n]
        crc_expected = struct.unpack(">I", raw[pos+8+n:end])[0]
        if zlib.crc32(kind + chunk) & 0xffffffff != crc_expected:
            raise ValueError("incorrect PNG chunk CRC")
        if not saw_ihdr:
            if kind != b"IHDR" or n != 13:
                raise ValueError("PNG IHDR must appear first")
            width, height, depth, color, compress, filt, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
            # Yabause/lodepng may use low-bit grayscale or indexed-color PNGs
            # for early frames. Accept only legal PNG bit-depth/color pairs.
            if color == 0:
                valid_depths = (1, 2, 4, 8, 16)
            elif color == 3:
                valid_depths = (1, 2, 4, 8)
            else:
                valid_depths = (8, 16)
            if (not 1 <= width <= 4096 or not 1 <= height <= 4096 or
                    depth not in valid_depths or color not in (0, 2, 3, 4, 6) or
                    compress != 0 or filt != 0 or interlace not in (0, 1)):
                raise ValueError("unsupported PNG frame shape")
            saw_ihdr = True
        elif kind == b"IHDR":
            raise ValueError("duplicate PNG header")
        if kind == b"PLTE":
            if (not saw_ihdr or saw_plte or saw_idat or color in (0, 4) or
                    n == 0 or n > 768 or n % 3 != 0 or
                    (color == 3 and n // 3 > (1 << depth))):
                raise ValueError("invalid PNG palette")
            saw_plte = True
        if kind == b"IDAT":
            if saw_iend:
                raise ValueError("PNG data after IEND")
            if color == 3 and not saw_plte:
                raise ValueError("indexed PNG missing palette")
            saw_idat = True
        if kind == b"IEND":
            if n != 0 or not saw_idat or end != len(raw):
                raise ValueError("invalid or nonterminal IEND")
            saw_iend = True
            break
        pos = end
    if not saw_ihdr or not saw_idat or not saw_iend:
        raise ValueError("incomplete PNG structure")
    if color == 3 and not saw_plte:
        raise ValueError("indexed PNG missing palette")
    return width, height


def audit_frame_witnesses(
    sessions: list[tuple[str, Path, Path]], *, track1_sectors: int | None = None,
) -> dict:
    if (not isinstance(sessions, list) or len(sessions) != 4 or
            any(not isinstance(p, tuple) or len(p) != 3 for p in sessions)):
        raise ValueError("four capture/witness triples required")
    # Reuse all Stage95 source/capture and FAD/ISO data-track checks.
    cohort, _ = audit_four_capture_cohort(
        [(phase, capture) for phase, capture, _ in sessions],
        track1_sectors=track1_sectors,
    )
    seen_dir, seen_frame_files = set(), set()
    matching_images = 0
    for phase, capture_dir, witness_dir in sessions:
        _private_directory(witness_dir)
        ino = (witness_dir.stat().st_dev, witness_dir.stat().st_ino)
        if ino in seen_dir or ino == (
            capture_dir.stat().st_dev, capture_dir.stat().st_ino
        ):
            raise ValueError("witness directory reused")
        seen_dir.add(ino)
        if {p.name for p in witness_dir.iterdir()} != {
            WITNESS_NAME, "before.png", "after.png"
        }:
            raise ValueError("unexpected private frame evidence files")
        manifest = _json_receipt(witness_dir / WITNESS_NAME)
        capture_receipt = _json_receipt(capture_dir / RECEIPT_FILE)
        session_id = manifest.get("session_id")
        if (not isinstance(session_id, str) or
                SESSION.fullmatch(session_id) is None or
                session_id != capture_receipt.get("session_id") or
                manifest.get("phase") != phase):
            raise ValueError("frame witness does not identify same capture")
        log = _private_regular(capture_dir / LOG_FILE, 400000)
        trace_hash = manifest.get("numeric_fad_sha256")
        if (not isinstance(trace_hash, str) or
                HEX_SHA.fullmatch(trace_hash) is None or
                hashlib.sha256(log).hexdigest() != trace_hash):
            raise ValueError("observed numeric log not bound to sidecar")
        frames = manifest.get("frames")
        if (not isinstance(frames, list) or len(frames) != 2 or
                [x.get("when") if isinstance(x, dict) else None for x in frames]
                != list(ALLOWED_STAGES)):
            raise ValueError("must present ordered before/after frame witness")
        sizes, digests, sequence = [], [], []
        for record, name in zip(frames, ("before.png", "after.png")):
            if record.get("file") != name:
                raise ValueError("witness filename not exact")
            counter = record.get("declared_frame_counter")
            if type(counter) is not int or not 0 <= counter < 10_000_000:
                raise ValueError("invalid declared frame counter")
            digest = record.get("sha256")
            if not isinstance(digest, str) or HEX_SHA.fullmatch(digest) is None:
                raise ValueError("invalid screenshot digest")
            path = witness_dir / name
            fs = path.lstat()
            key = (fs.st_dev, fs.st_ino)
            if key in seen_frame_files:
                raise ValueError("screenshot file reused between sessions")
            seen_frame_files.add(key)
            raw = _private_regular(path, MAX_PNG)
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("screenshot bytes differ from witness digest")
            sizes.append(validate_png_file(raw))
            digests.append(digest)
            sequence.append(counter)
        if sizes[0] != sizes[1] or sequence[0] >= sequence[1]:
            raise ValueError("different frame shapes or nonmonotone declared frames")
        matching_images += digests[0] == digests[1]
    return {
        "schema_version": 1,
        "kind": "STAGE96_PRIVATE_FRAME_WITNESS_FILE_INTEGRITY_ONLY",
        "stage95_cohort_sources_and_fad_verified": True,
        "private_witness_directories_verified": 4,
        "locally_present_frame_files_verified": 8,
        "per_file_sha256_and_png_framing_verified": True,
        "all_fad_logs_bound_by_sha256_to_frame_sidecars": True,
        "operator_declared_frame_counters_monotone": True,
        "unchanged_png_pairs": matching_images,
        "identical_images_may_be_legitimate": True,
        "actual_emulator_frame_counters_independently_verified": False,
        "frame_capture_synchronized_to_fad_gate_verified": False,
        "actual_original_saturn_game_boot_observed": False,
        "original_first_battle_scene_identified": False,
        "source_loader_to_map_relationship_verified": False,
        "original_media_or_frames_exported": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--menu-capture", type=Path, action="append", required=True)
    p.add_argument("--menu-witness", type=Path, action="append", required=True)
    p.add_argument("--battle-capture", type=Path, action="append", required=True)
    p.add_argument("--battle-witness", type=Path, action="append", required=True)
    args = p.parse_args()
    try:
        if any(len(x) != 2 for x in (
            args.menu_capture, args.menu_witness,
            args.battle_capture, args.battle_witness
        )):
            raise ValueError("exactly two of each phase needed")
        sources = (
            [("menu_control", c, w) for c, w in zip(
                args.menu_capture, args.menu_witness
            )] +
            [("first_battle_entry", c, w) for c, w in zip(
                args.battle_capture, args.battle_witness
            )]
        )
        result = audit_frame_witnesses(sources)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        print("STAGE96_FRAME_WITNESS_FILE_REJECTED", file=sys.stderr)
        return 1
    # No paths, hashes, content, frame pixels or original game assets printed.
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
