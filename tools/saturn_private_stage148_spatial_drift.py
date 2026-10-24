#!/usr/bin/env python3
"""Stage148: private spatial and SH2 correlation of two verified control captures.

The owner must independently verify provenance, full Stage144/145 paired audits,
runner and media SHA-256, private host identity, and Drive readback. This tool
does not prove cause, replay determinism, or battle control. It never exports
pixels, private register values, CD traces, or file hashes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from PIL import Image, ImageChops

from tools import saturn_private_same_session_cross_build_prefix as prefix
from tools.saturn_private_stage147_replay_matrix import _validate_capture


def _fields(line: str, kind: str) -> dict[str, str]:
    elements = line.split()
    if not elements or elements[0] != kind:
        raise ValueError("Stage148 diagnostic record kind invalid")
    record = {}
    for part in elements[1:]:
        if part.count("=") != 1:
            raise ValueError("Stage148 diagnostic field malformed")
        key, value = part.split("=")
        if not key or key in record or not key.replace("_", "").isalnum() or not value.isdecimal():
            raise ValueError("Stage148 diagnostic field key/value invalid")
        record[key] = value
    if "frame" not in record or "pc" not in record:
        raise ValueError("Stage148 mandatory diagnostic fields absent")
    return record


def _changed_fields(left: str, right: str, kind: str) -> tuple[str, ...]:
    a, b = _fields(left, kind), _fields(right, kind)
    if a["frame"] != b["frame"]:
        raise ValueError("Stage148 diagnostic frame keys differ")
    return tuple(sorted(k for k in set(a) | set(b) if k != "frame" and a.get(k) != b.get(k)))


def _pixel_regions(a: bytes, b: bytes, dims: tuple[int, int]) -> tuple[int, int]:
    if len(a) != len(b) or len(a) != dims[0] * dims[1] * 3:
        raise ValueError("Stage148 decoded framebuffer sizes differ")
    if a == b:
        return 0, 0
    left = Image.frombytes("RGB", dims, a)
    right = Image.frombytes("RGB", dims, b)
    channels = ImageChops.difference(left, right).split()
    mask = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    total = dims[0] * dims[1] - mask.histogram()[0]
    top_rows = max(1, dims[1] * 3 // 10)
    top_mask = mask.crop((0, 0, dims[0], top_rows))
    top = dims[0] * top_rows - top_mask.histogram()[0]
    if top > total:
        raise ValueError("Stage148 impossible regional pixel count")
    return top, total - top


def _phase(frame: int) -> str:
    if frame <= 24000:
        return "early_120_to_24000"
    if frame <= 60000:
        return "middle_24120_to_60000"
    return "late_60120_to_96000"


def audit_private_stage148_spatial_drift(stage144: Path, stage145: Path) -> dict:
    if stage144.resolve() == stage145.resolve():
        raise ValueError("Stage148 requires two distinct capture folders")
    _validate_capture(stage144, 0)
    _validate_capture(stage145, 2)

    sh2 = [prefix._read_frame_diagnostics(p, "sh2-window.txt", prefix.SH2_LINE)
           for p in (stage144, stage145)]
    video = [prefix._read_frame_diagnostics(p, "video-state.txt", prefix.VIDEO_LINE)
             for p in (stage144, stage145)]
    fad = [prefix._read_fad(p) for p in (stage144, stage145)]
    buckets = {
        phase: {
            "total_checkpoints": 0,
            "pixel_differing_checkpoints": 0,
            "top_band_pixel_differences": 0,
            "lower_band_pixel_differences": 0,
            "sh2_changed_record_count": 0,
            "video_changed_record_count": 0,
            "sh2_changed_fields": Counter(),
            "video_changed_fields": Counter(),
        } for phase in ("early_120_to_24000", "middle_24120_to_60000",
                        "late_60120_to_96000")
    }
    dims_expected = None
    for frame in prefix.CHECKPOINTS:
        a_dims, a_rgb = prefix._read_rgb(stage144, frame, dims_expected)
        b_dims, b_rgb = prefix._read_rgb(stage145, frame, dims_expected)
        if a_dims != b_dims:
            raise ValueError("Stage148 framebuffer dimensions differ")
        dims_expected = a_dims
        bucket = buckets[_phase(frame)]
        bucket["total_checkpoints"] += 1
        top, bottom = _pixel_regions(a_rgb, b_rgb, a_dims)
        if top or bottom:
            bucket["pixel_differing_checkpoints"] += 1
            bucket["top_band_pixel_differences"] += top
            bucket["lower_band_pixel_differences"] += bottom
        for label, values, kind in (("sh2", sh2, "VH_SH2"), ("video", video, "VH_VIDEO")):
            changed = _changed_fields(values[0][frame], values[1][frame], kind)
            if changed:
                bucket[f"{label}_changed_record_count"] += 1
                bucket[f"{label}_changed_fields"].update(changed)

    for bucket in buckets.values():
        bucket["sh2_changed_fields"] = dict(sorted(bucket["sh2_changed_fields"].items()))
        bucket["video_changed_fields"] = dict(sorted(bucket["video_changed_fields"].items()))
        bucket["top_band_exclusive_when_different"] = (
            bucket["pixel_differing_checkpoints"] > 0 and
            bucket["lower_band_pixel_differences"] == 0
        )

    common_fad = 0
    for aa, bb in zip(fad[0], fad[1]):
        if aa != bb:
            break
        common_fad += 1
    return {
        "schema": "vh-saturn-stage148-private-spatial-sh2-correlation-1",
        "kind": "STAGE148_PRIVATE_SPATIAL_AND_SH2_CORRELATION",
        "frame_start": prefix.FRAME_START,
        "frame_end": prefix.FRAME_END,
        "frame_step": prefix.FRAME_STEP,
        "band_rule": "top_floor_30_percent_of_framebuffer_height",
        "total_compared_checkpoints": len(prefix.CHECKPOINTS),
        "phases": buckets,
        "fad_common_prefix_record_count": common_fad,
        "fad_equal": fad[0] == fad[1],
        "runner_and_media_provenance_verified_by_this_tool": False,
        "same_host_and_replay_repeatability_verified": False,
        "causal_source_of_drift_established": False,
        "original_media_or_frame_hashes_exported": False,
        "private_register_values_exported": False,
        "battle_or_tactical_player_control_verified": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage144-control", required=True, type=Path)
    p.add_argument("--stage145-control", required=True, type=Path)
    args = p.parse_args()
    try:
        result = audit_private_stage148_spatial_drift(args.stage144_control,
                                                      args.stage145_control)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("STAGE148_PRIVATE_SPATIAL_DRIFT_REJECTED", type(exc).__name__, str(exc),
              file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
