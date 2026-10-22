#!/usr/bin/env python3
"""Stage101: validate only a local numeric VDP/Titan trace, never screen bytes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from tools.saturn_private_capture_cohort import _private_directory, _private_regular

FIELDS = (
    "frame", "pc", "tvmd", "bgon", "ramctl", "vdp1_tvmr",
    "vdp1_ptmr", "vdp1_edsr", "vdp1_nz", "vdp2_nz",
    "cram_nz", "rgb_nz", "width", "height",
)
PATTERN = re.compile(
    rb"VH_VIDEO " +
    rb" ".join(field.encode() + rb"=(0|[1-9][0-9]*)" for field in FIELDS) +
    rb"\Z"
)
BOUNDS = {
    "frame": 600, "pc": 0xffffffff,
    "tvmd": 0xffff, "bgon": 0xffff, "ramctl": 0xffff,
    "vdp1_tvmr": 0xffff, "vdp1_ptmr": 0xffff, "vdp1_edsr": 0xffff,
    "vdp1_nz": 0x80000, "vdp2_nz": 0x80000,
    "cram_nz": 0x1000, "width": 704, "height": 512,
}


def parse_video_state(data: bytes) -> dict:
    if (not isinstance(data, bytes) or not 0 < len(data) <= 131072 or
            not data.endswith(b"\n") or b"\r" in data or b"\0" in data):
        raise ValueError("noncanonical private numeric video status")
    samples = []
    for line in data.splitlines():
        match = PATTERN.fullmatch(line)
        if match is None:
            raise ValueError("unexpected private video status record")
        obj = dict(zip(FIELDS, map(int, match.groups())))
        for field, maximum in BOUNDS.items():
            if obj[field] > maximum:
                raise ValueError("unexpected VDP/frame range")
        if (not 1 <= obj["width"] <= 704 or not 1 <= obj["height"] <= 512 or
                obj["rgb_nz"] > obj["width"] * obj["height"]):
            raise ValueError("invalid reported rendered pixel count")
        if samples:
            if obj["frame"] < samples[-1]["frame"]:
                raise ValueError("nonmonotone observed emulator frame counter")
            if obj["frame"] == samples[-1]["frame"] and obj != samples[-1]:
                raise ValueError("same frame conflicting numeric video readings")
            if obj["frame"] == samples[-1]["frame"] and obj == samples[-1]:
                continue  # Stage99 writes a 600 checkpoint and final frame.
        samples.append(obj)
    if len(samples) < 2 or samples[0]["frame"] != 0 or samples[-1]["frame"] == 0:
        raise ValueError("video diagnostics missing before/after frame observations")
    if any(s["frame"] % 120 for s in samples[1:-1]):
        raise ValueError("unexpected private checkpoint frame")
    return {
        "schema_version": 1,
        "kind": "STAGE101_PRIVATE_NUMERIC_VDP_VIDEO_EVIDENCE_ONLY",
        "numeric_samples": len(samples),
        "final_emulated_frame": samples[-1]["frame"],
        "final_video_width": samples[-1]["width"],
        "final_video_height": samples[-1]["height"],
        "final_tvmd_display_enable_bit": bool(samples[-1]["tvmd"] & 0x8000),
        "final_background_layers_enabled": samples[-1]["bgon"] != 0,
        "final_vdp1_ram_has_nonzero_data": samples[-1]["vdp1_nz"] > 0,
        "final_vdp2_ram_has_nonzero_data": samples[-1]["vdp2_nz"] > 0,
        "final_color_ram_has_nonzero_data": samples[-1]["cram_nz"] > 0,
        "frames_with_nonblack_titan_pixels": [
            sample["frame"] for sample in samples if sample["rgb_nz"] > 0
        ],
        "vdp2_state_changes_observed": len({
            (x["tvmd"], x["bgon"], x["ramctl"]) for x in samples
        }) > 1,
        "sh2_pc_changes_observed": len({x["pc"] for x in samples}) > 1,
        "actual_original_game_title_visible_verified": False,
        "original_first_battle_visible_verified": False,
        "frame_to_cd_reads_synchronized_verified": False,
        "video_ram_payload_exported": False,
    }


def inspect_private_video_file(path: Path) -> dict:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError("absolute protected local video-state path required")
    _private_directory(path.parent)
    data = _private_regular(path, 131072)
    return parse_video_state(data)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video-state", required=True, type=Path)
    a = p.parse_args()
    try:
        summary = inspect_private_video_file(a.video_state)
    except (OSError, ValueError, TypeError):
        print("STAGE101_PRIVATE_VIDEO_STATE_REJECTED", file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
