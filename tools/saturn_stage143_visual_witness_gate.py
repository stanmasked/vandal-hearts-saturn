#!/usr/bin/env python3
"""Stage143 visual-witness quality gate for private paired Saturn checkpoints.

Uses only the Python standard library. Validates PNG structure, CRCs, dimensions,
scanline decoding and pixel content. It detects all-black checkpoint runs that
are bracketed by non-black checkpoints; such spans are review-required, not
automatically attributed to the emulator or the game.

The report contains only counts and frame indices, never image bytes or hashes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PNG_BYTES = 16_777_216
WIDTH, HEIGHT = 352, 240
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
VALID_DEPTHS = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _samples(row: bytes, bit_depth: int, count: int):
    if bit_depth == 8:
        if len(row) < count:
            raise ValueError("PNG scanline too short")
        yield from row[:count]
        return
    if bit_depth == 16:
        if len(row) < count * 2:
            raise ValueError("PNG scanline too short")
        for i in range(0, count * 2, 2):
            yield (row[i] << 8) | row[i+1]
        return
    if bit_depth not in (1, 2, 4):
        raise ValueError("unsupported PNG sample depth")
    for i in range(count):
        bit = i * bit_depth
        shift = 8 - bit_depth - (bit % 8)
        yield (row[bit // 8] >> shift) & ((1 << bit_depth) - 1)


def _decode_is_black(blob: bytes) -> bool:
    if blob[:8] != PNG_SIGNATURE or not 33 <= len(blob) <= MAX_PNG_BYTES:
        raise ValueError("PNG signature/size invalid")
    offset = 8
    ihdr = None
    palette = None
    idat = bytearray()
    saw_idat = False
    ended_idat = False
    saw_iend = False
    while offset < len(blob):
        if offset + 12 > len(blob):
            raise ValueError("PNG truncated chunk header")
        length = struct.unpack(">I", blob[offset:offset+4])[0]
        kind = blob[offset+4:offset+8]
        end = offset + 12 + length
        if length > MAX_PNG_BYTES or end > len(blob):
            raise ValueError("PNG chunk length invalid")
        payload = blob[offset+8:offset+8+length]
        stored_crc = struct.unpack(">I", blob[offset+8+length:end])[0]
        if zlib.crc32(kind + payload) & 0xffffffff != stored_crc:
            raise ValueError("PNG CRC mismatch")
        if ihdr is None and (kind != b"IHDR" or length != 13):
            raise ValueError("PNG IHDR missing or misplaced")
        if kind == b"IHDR":
            if ihdr is not None or offset != 8:
                raise ValueError("PNG duplicate/misplaced IHDR")
            ihdr = struct.unpack(">IIBBBBB", payload)
        elif kind == b"PLTE":
            if saw_idat or length == 0 or length % 3 or length > 768:
                raise ValueError("PNG palette invalid")
            palette = payload
        elif kind == b"IDAT":
            if ended_idat:
                raise ValueError("PNG nonconsecutive IDAT chunks")
            saw_idat = True
            idat.extend(payload)
            if len(idat) > MAX_PNG_BYTES:
                raise ValueError("PNG compressed image data oversized")
        elif kind == b"IEND":
            if length != 0 or end != len(blob) or not saw_idat:
                raise ValueError("PNG IEND invalid or image data absent")
            saw_iend = True
            offset = end
            break
        else:
            if saw_idat:
                ended_idat = True
            if kind[0] & 0x20 == 0 and kind not in (b"IHDR", b"PLTE", b"IDAT", b"IEND"):
                raise ValueError("PNG unknown critical chunk")
        if kind != b"IDAT" and saw_idat:
            ended_idat = True
        offset = end
    if not saw_iend or offset != len(blob) or ihdr is None:
        raise ValueError("PNG incomplete")
    width, height, depth, color_type, compression, filt, interlace = ihdr
    if (width, height) != (WIDTH, HEIGHT):
        raise ValueError("PNG dimensions invalid")
    if (color_type not in CHANNELS or depth not in VALID_DEPTHS[color_type] or
            compression != 0 or filt != 0 or interlace != 0):
        raise ValueError("PNG encoding mode unsupported")
    if color_type == 3 and (palette is None or len(palette) // 3 > (1 << depth)):
        raise ValueError("PNG indexed palette missing or oversized")
    channels = CHANNELS[color_type]
    row_bytes = (width * channels * depth + 7) // 8
    bytes_per_pixel = max(1, (channels * depth + 7) // 8)
    expected = (row_bytes + 1) * height
    inflater = zlib.decompressobj()
    raw = inflater.decompress(bytes(idat), expected + 1)
    if len(raw) > expected or inflater.unconsumed_tail or not inflater.eof or inflater.unused_data:
        raise ValueError("PNG decompressed length invalid")
    raw += inflater.flush()
    if len(raw) != expected:
        raise ValueError("PNG scanline length invalid")
    previous = bytearray(row_bytes)
    black = True
    pos = 0
    palette_colors = [tuple(palette[i:i+3]) for i in range(0, len(palette or b""), 3)]
    for _y in range(height):
        filter_type = raw[pos]
        filtered = raw[pos+1:pos+1+row_bytes]
        pos += row_bytes + 1
        row = bytearray(row_bytes)
        if filter_type > 4:
            raise ValueError("PNG scanline filter invalid")
        for i, x in enumerate(filtered):
            left = row[i-bytes_per_pixel] if i >= bytes_per_pixel else 0
            up = previous[i]
            upper_left = previous[i-bytes_per_pixel] if i >= bytes_per_pixel else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            else:
                predictor = _paeth(left, up, upper_left)
            row[i] = (x + predictor) & 0xff
        if color_type == 0:
            if any(v != 0 for v in _samples(row, depth, width)):
                black = False
        elif color_type == 2:
            if any(v != 0 for v in _samples(row, depth, width * 3)):
                black = False
        elif color_type == 3:
            for idx in _samples(row, depth, width):
                if idx >= len(palette_colors):
                    raise ValueError("PNG palette index out of range")
                if palette_colors[idx] != (0, 0, 0):
                    black = False
        elif color_type == 4:
            values = iter(_samples(row, depth, width * 2))
            for gray, _alpha in zip(values, values):
                if gray != 0:
                    black = False
        else:  # RGBA; alpha does not change whether RGB samples are black.
            values = iter(_samples(row, depth, width * 4))
            for r, g, b, _alpha in zip(values, values, values, values):
                if r != 0 or g != 0 or b != 0:
                    black = False
        previous = row
    return black


def _black_runs(frames: tuple[int, ...], mask: tuple[bool, ...]) -> list[dict[str, int]]:
    runs = []
    i = 0
    while i < len(mask):
        if not mask[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(mask) and mask[j+1]:
            j += 1
        # A boot-time black prefix is allowed if the display later appears.
        # Internal and trailing black spans require review; an all-black
        # sequence is always rejected.
        if i > 0:
            runs.append({"first_frame": frames[i], "last_frame": frames[j], "count": j-i+1})
        i = j + 1
    if mask and all(mask) and not runs:
        runs.append({"first_frame": frames[0], "last_frame": frames[-1], "count": len(frames)})
    return runs


def audit_visual_witness(control: Path, enabled: Path, *, through_frame: int = 24000,
                         reviewed_black_runs: tuple[tuple[int, int], ...] = ()) -> dict:
    if (type(through_frame) is not int or through_frame < 240 or through_frame % 120 or
            through_frame >= 108000):
        raise ValueError("invalid pre-tenth checkpoint window")
    reviewed = []
    for pair in reviewed_black_runs:
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise ValueError("reviewed black span must be a start/end pair")
        first, last = pair
        if (type(first) is not int or type(last) is not int or first < 120 or first > last or
                last > through_frame or first % 120 or last % 120):
            raise ValueError("reviewed black span is outside the checkpoint window")
        reviewed.append((first, last))
    reviewed = tuple(sorted(reviewed))
    if len(set(reviewed)) != len(reviewed):
        raise ValueError("duplicate reviewed black span")
    if any(reviewed[i][1] >= reviewed[i+1][0] for i in range(len(reviewed)-1)):
        raise ValueError("overlapping reviewed black spans")
    if (control.is_symlink() or enabled.is_symlink() or not control.is_dir() or not enabled.is_dir()
            or control.resolve() == enabled.resolve()):
        raise ValueError("two independent private capture directories required")
    frames = tuple(range(120, through_frame + 1, 120))
    masks = []
    for folder in (control, enabled):
        black = []
        for frame in frames:
            path = folder / f"frame-{frame}.png"
            if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_PNG_BYTES:
                raise ValueError("checkpoint PNG missing or unsafe")
            black.append(_decode_is_black(path.read_bytes()))
        masks.append(tuple(black))
    control_mask, enabled_mask = masks
    runs_control = _black_runs(frames, control_mask)
    runs_enabled = _black_runs(frames, enabled_mask)
    visible_control = sum(not x for x in control_mask)
    visible_enabled = sum(not x for x in enabled_mask)
    mask_equal = control_mask == enabled_mask
    control_ranges = tuple((x["first_frame"], x["last_frame"]) for x in runs_control)
    enabled_ranges = tuple((x["first_frame"], x["last_frame"]) for x in runs_enabled)
    reviewed_match = bool(control_ranges == enabled_ranges and reviewed == control_ranges)
    reviewed_set = set(reviewed)
    unreviewed_control = [x for x in runs_control if (x["first_frame"], x["last_frame"]) not in reviewed_set]
    unreviewed_enabled = [x for x in runs_enabled if (x["first_frame"], x["last_frame"]) not in reviewed_set]
    accepted = bool(mask_equal and visible_control and visible_enabled and reviewed_match)
    return {
        "schema": "vh-saturn-stage143-visual-witness-gate-1",
        "stage": 143,
        "through_frame": through_frame,
        "checkpoint_pairs_decoded": len(frames),
        "control_black_checkpoint_count": sum(control_mask),
        "enabled_black_checkpoint_count": sum(enabled_mask),
        "control_black_prefix_count": next((i for i, x in enumerate(control_mask) if not x), len(frames)),
        "enabled_black_prefix_count": next((i for i, x in enumerate(enabled_mask) if not x), len(frames)),
        "control_suspect_black_runs": runs_control,
        "enabled_suspect_black_runs": runs_enabled,
        "reviewed_black_runs": [{"first_frame": a, "last_frame": b} for a, b in reviewed],
        "unreviewed_black_runs_control": unreviewed_control,
        "unreviewed_black_runs_enabled": unreviewed_enabled,
        "reviewed_black_runs_match_both_cohorts": reviewed_match,
        "reviewed_black_runs_are_explicit_allowlist": True,
        "black_classification_masks_match": mask_equal,
        "visual_witness_accepted": accepted,
        "requires_visual_review": not accepted,
        "original_media_or_frame_hashes_exported": False,
        "full_original_game_run_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--enabled", type=Path, required=True)
    parser.add_argument("--through-frame", type=int, default=24000)
    parser.add_argument("--reviewed-black-run", action="append", default=[], metavar="START:END",
                        help="explicitly reviewed black checkpoint span; repeat for each exact run")
    args = parser.parse_args()
    try:
        reviewed = []
        for item in args.reviewed_black_run:
            parts = item.split(":")
            if len(parts) != 2:
                raise ValueError("reviewed black span must be START:END")
            reviewed.append((int(parts[0]), int(parts[1])))
        report = audit_visual_witness(args.control, args.enabled, through_frame=args.through_frame,
                                      reviewed_black_runs=tuple(reviewed))
    except (OSError, ValueError, UnicodeError, struct.error, zlib.error):
        print("STAGE143_VISUAL_WITNESS_REJECTED_INVALID_CAPTURE", file=sys.stderr)
        return 1
    if not report["visual_witness_accepted"]:
        print("STAGE143_VISUAL_WITNESS_REQUIRES_REVIEW", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
