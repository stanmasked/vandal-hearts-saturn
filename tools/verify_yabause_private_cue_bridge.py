#!/usr/bin/env python3
"""Stage88: integrate the Stage87 private wrapper with real pinned Yabause CUE I/O.

This module NEVER accepts a user disc. It creates tiny artificial two-sector
MODE1/2352 BIN + CUE fixtures and a separate invented companion track.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from tools.saturn_private_capture_session import capture_private, LOG_FILE, RECEIPT_FILE

GOOD_LOG = b"VHCD_FAD 150\nVHCD_FAD 151\n"
TRACK1_NAME = "stage88-fabricated-track1.bin"
TRACK2_NAME = "stage88-fabricated-track2.bin"
CUE_NAME = "stage88-fabricated-disc.CUE"
MODE = "vh-exact-cue-read"


def make_fake_disc(directory: Path) -> tuple[dict, dict]:
    if not directory.is_dir() or any(directory.iterdir()):
        raise ValueError("empty synthetic source directory required")
    raw = bytearray(2352 * 2)
    raw[0:2] = bytes([17, 18])
    raw[2352:2354] = bytes([50, 51])
    # This is not a Saturn MODE1 sector or any recognized game data.
    raw[2:2352] = bytes(((k * 13 + 3) & 255) for k in range(2350))
    raw[2354:] = bytes(((k * 17 + 5) & 255) for k in range(2350))
    track1 = directory / TRACK1_NAME
    track2 = directory / TRACK2_NAME
    cue = directory / CUE_NAME
    track1.write_bytes(raw)
    track2.write_bytes(b"INVENTED NONDISC TRACK2 " + bytes(100))
    cue.write_bytes((
        'FILE "' + TRACK1_NAME + '" BINARY\n'
        '  TRACK 01 MODE1/2352\n'
        '    INDEX 01 00:00:00\n'
    ).encode("ascii"))
    files = {"track1": track1, "track2": track2, "cue": cue}
    pins = {
        k: (len(p.read_bytes()), hashlib.sha256(p.read_bytes()).hexdigest())
        for k, p in files.items()
    }
    manifest = {
        "schema_version": 1,
        "product_code": "T-9526G",  # Test of wrapper schema, not product authentication.
        "release_kind": "translation_patched",
        "files": {k: str(p) for k, p in files.items()},
    }
    return manifest, pins


def verify_real_pinned_cue(executable: Path, root: Path) -> dict:
    runner = executable.resolve(strict=True)
    if (not runner.is_file() or not os.access(runner, os.X_OK) or
            not root.is_absolute() or not root.is_dir() or any(root.iterdir())):
        raise ValueError("real runner and empty absolute private workspace required")
    source_dir = root / "invented-source"
    source_dir.mkdir(mode=0o700)
    manifest, pins = make_fake_disc(source_dir)
    runner_pin = hashlib.sha256(runner.read_bytes()).hexdigest()
    first = root / "capture-valid-cue"
    first.mkdir(mode=0o700)
    result = capture_private(
        manifest, first, "menu_control", [str(runner), MODE, manifest["files"]["cue"]],
        seconds=20, pins=pins, expected_executable_sha256=runner_pin,
    )
    if ((first / LOG_FILE).read_bytes() != GOOD_LOG or
            result["numeric_fad_events"] != 2 or
            result["game_disc_actually_opened_verified"] or
            result["original_game_execution_verified"] or
            not result["runner_matches_separately_supplied_sha256"] or
            not result["cue_path_exactly_present_in_command"]):
        raise ValueError("real CUE run did not meet synthetic-only evidence contract")
    # Negative control: an otherwise well-formed CUE points to a
    # NONEXISTENT BIN. Re-pin only this invented fake CUE, not game media.
    bad_dir = root / "invented-bad-source"
    bad_dir.mkdir(mode=0o700)
    bad_manifest, bad_pins = make_fake_disc(bad_dir)
    bad_path = Path(bad_manifest["files"]["cue"])
    bad_path.write_text(
        'FILE "missing-fabricated.bin" BINARY\n'
        '  TRACK 01 MODE1/2352\n'
        '    INDEX 01 00:00:00\n', encoding="ascii",
    )
    bad_pins["cue"] = (
        bad_path.stat().st_size,
        hashlib.sha256(bad_path.read_bytes()).hexdigest(),
    )
    second = root / "capture-missing-bin"
    second.mkdir(mode=0o700)
    try:
        capture_private(
            bad_manifest, second, "menu_control",
            [str(runner), MODE, bad_manifest["files"]["cue"]],
            seconds=20, pins=bad_pins, expected_executable_sha256=runner_pin,
        )
    except ValueError:
        if (second / RECEIPT_FILE).exists():
            raise ValueError("rejected source emitted success receipt")
    else:
        raise ValueError("emulator incorrectly accepted CUE with missing BIN")
    return {
        "stage": 88,
        "pinned_real_public_yabause_binary": True,
        "synthetic_cue_and_track1_opened_in_real_backend": True,
        "negative_missing_bin_rejected": True,
        "exact_numeric_fad_records": 2,
        "private_wrapper_source_and_runner_pins_agree": True,
        "real_game_media_used": False,
        "original_game_boot_verified": False,
        "first_battle_loader_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix="vh-stage88-synthetic-") as tmp:
            root = Path(tmp)
            root.chmod(0o700)
            result = verify_real_pinned_cue(args.executable, root)
        print(json.dumps(result, sort_keys=True))
        print("STAGE88_REAL_YABAUSE_PRIVATE_WRAPPER_CUE_OPEN_PASS")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        print("STAGE88_SYNTHETIC_CUE_BRIDGE_REJECTED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
