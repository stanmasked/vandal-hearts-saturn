#!/usr/bin/env python3
"""End-to-end C++17 fingerprint -> PPM pixels -> Python image decoder test.

Requires a host-compiled vh_visual_fixture and Pillow. Original Saturn assets
and the Switch SDK are not used by this protocol verification.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

from PIL import Image
from tools.nexium_visual_digest import decode, INITIAL_TRAINING_FINGERPRINT


def verify(binary: Path) -> dict:
    if not binary.is_file():
        raise FileNotFoundError(binary)
    with tempfile.TemporaryDirectory(prefix="vhsaturn-visual-") as td:
        result = subprocess.run([str(binary.resolve()), td], capture_output=True,
                                text=True, timeout=20, check=True)
        lines = result.stdout.splitlines()
        if len(lines) != 2 or not all(re.fullmatch(r"(initial|moved)=[0-9a-f]{16}", x) for x in lines):
            raise ValueError("Unexpected native image fixture receipt format")
        fields = dict(line.split("=", 1) for line in lines)
        if set(fields) != {"initial", "moved"}:
            raise ValueError("Missing initial/moved fixture fingerprints")
        if fields["initial"] != INITIAL_TRAINING_FINGERPRINT or fields["initial"] == fields["moved"]:
            raise AssertionError("Native replay golden differs or did not change after move")
        with Image.open(Path(td) / "initial.ppm") as original:
            initial = decode(original, fields["initial"])
            stale = decode(original, fields["moved"])
            assert initial["matches_expected_training_state"]
            assert not stale["matches_expected_training_state"]
            assert initial["anchors_found"] == 3 and initial["unrecognized_cells"] == 0
            damaged = original.convert("RGB")
            damaged.putpixel((24, 24), (255, 255, 255))
            assert not decode(damaged, fields["initial"])["matches_expected_training_state"]
        with Image.open(Path(td) / "moved.ppm") as changed:
            moved = decode(changed, fields["moved"])
            still_initial = decode(changed, fields["initial"])
            assert moved["matches_expected_training_state"]
            assert not still_initial["matches_expected_training_state"]
        return {
            "fixture_origin": "native_C++_rom_free_training_scene",
            "image_format": "PPM_P6_RGB_1280x720",
            "initial_fingerprint": fields["initial"],
            "moved_fingerprint": fields["moved"],
            "checks": {
                "initial_native_to_python": True,
                "moved_native_to_python": True,
                "stale_reference_rejected": True,
                "corrupted_pixel_rejected": True,
                "anchors_present": True,
            },
            "NeXium_runtime_validated": False,
            "original_Saturn_content": False,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = verify(args.binary)
    report = json.dumps(receipt, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
