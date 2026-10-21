#!/usr/bin/env python3
"""Stage89: real Yabause split BIN/CUE test, exclusively invented sector bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from tools.saturn_private_capture_session import (
    LOG_FILE, RECEIPT_FILE, capture_private,
)

DATA = "invented-track01.bin"
AUDIO = "invented-track02.bin"
CUE = "invented-split.CUE"
MODE = "vh-two-file-cue-read"
EXPECTED = b"VHCD_FAD 150\nVHCD_FAD 151\nVHCD_FAD 302\nVHCD_FAD 303\n"


def make_split_fixture(directory: Path) -> tuple[dict, dict]:
    if not directory.is_dir() or any(directory.iterdir()):
        raise ValueError("new empty fixture directory required")
    track1 = bytearray(2 * 2352)
    track1[:2], track1[2352:2354] = bytes([17, 18]), bytes([50, 51])
    # Invented second track: 150 raw pregap sectors + two active samples.
    track2 = bytearray(152 * 2352)
    track2[150*2352:150*2352+2] = bytes([77, 78])
    track2[151*2352:151*2352+2] = bytes([88, 89])
    paths = {
        "track1": directory / DATA,
        "track2": directory / AUDIO,
        "cue": directory / CUE,
    }
    paths["track1"].write_bytes(track1)
    paths["track2"].write_bytes(track2)
    paths["cue"].write_text(
        'CATALOG 0000000000000\n'
        'FILE "' + DATA + '" BINARY\n'
        '  TRACK 01 MODE1/2352\n'
        '    INDEX 01 00:00:00\n'
        'FILE "' + AUDIO + '" BINARY\n'
        '  TRACK 02 AUDIO\n'
        '    INDEX 00 00:00:00\n'
        '    INDEX 01 00:02:00\n',
        encoding="ascii",
    )
    pins = {
        name: (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
        for name, p in paths.items()
    }
    return ({
        "schema_version": 1,
        "product_code": "T-9526G",  # Fabricated schema-only label.
        "release_kind": "translation_patched",
        "files": {k: str(v) for k, v in paths.items()},
    }, pins)


def verify_split_track_open(runner: Path, root: Path) -> dict:
    exe = runner.resolve(strict=True)
    if not exe.is_file() or not os.access(exe, os.X_OK) or not root.is_absolute() \
            or not root.is_dir() or any(root.iterdir()):
        raise ValueError("requires real executable and new private workspace")
    pin = hashlib.sha256(exe.read_bytes()).hexdigest()
    src = root / "fabricated-tracks"
    src.mkdir(mode=0o700)
    manifest, pins = make_split_fixture(src)
    target = root / "accepted-two-file-cue"
    target.mkdir(mode=0o700)
    receipt = capture_private(
        manifest, target, "menu_control",
        [str(exe), MODE, manifest["files"]["cue"]],
        seconds=20, pins=pins, expected_executable_sha256=pin,
    )
    if ((target / LOG_FILE).read_bytes() != EXPECTED or
            receipt["numeric_fad_events"] != 4 or
            not receipt["pinned_files_unchanged_after_run"] or
            not receipt["runner_matches_separately_supplied_sha256"] or
            receipt["original_game_execution_verified"]):
        raise ValueError("genuine Yabause split tracks did not match expected receipt")

    # Two independent, malformed synthetic inputs must be rejected without
    # a success receipt: a missing AUDIO BIN, and an incorrect INDEX01.
    for kind in ("missing-audio-file", "wrong-pregap-index"):
        sub = root / ("invented-" + kind)
        sub.mkdir(mode=0o700)
        m, pins_bad = make_split_fixture(sub)
        if kind == "missing-audio-file":
            (sub / AUDIO).unlink()
            # Preserve a locally pinned path that no longer exists:
            # the source wrapper will fail before launching Yabause.
        else:
            cue = sub / CUE
            cue.write_text(cue.read_text().replace(
                "INDEX 01 00:02:00", "INDEX 01 00:01:00"
            ), encoding="ascii")
            pins_bad["cue"] = (
                cue.stat().st_size, hashlib.sha256(cue.read_bytes()).hexdigest()
            )
        out = root / ("rejected-" + kind)
        out.mkdir(mode=0o700)
        try:
            capture_private(
                m, out, "menu_control",
                [str(exe), MODE, m["files"]["cue"]],
                seconds=20, pins=pins_bad, expected_executable_sha256=pin,
            )
        except (ValueError, OSError):
            if (out / RECEIPT_FILE).exists():
                raise ValueError("bad two-file CUE issued a success receipt")
        else:
            raise ValueError("bad two-file CUE accepted")
    return {
        "stage": 89,
        "real_public_yabause_split_cue_opened": True,
        "synthetic_data_sectors": 2,
        "synthetic_audio_sectors_after_pregap": 2,
        "audio_index01_fad": 302,
        "numeric_fad_receipts": 4,
        "negative_inputs_rejected": 2,
        "single_file_stage88_compatibility_checked_by_workflow": True,
        "original_game_media_present": False,
        "authentic_saturn_boot_verified": False,
        "authentic_two_track_audio_playback_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix="stage89-fabricated-") as td:
            root = Path(td)
            root.chmod(0o700)
            result = verify_split_track_open(args.executable, root)
        print(json.dumps(result, sort_keys=True))
        print("STAGE89_REAL_YABAUSE_TWO_FILE_CUE_PASS")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        print("STAGE89_TWO_FILE_CUE_TEST_REJECTED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
