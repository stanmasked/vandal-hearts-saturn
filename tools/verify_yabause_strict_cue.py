#!/usr/bin/env python3
"""Stage91: genuine pinned Yabause rejects malformed invented split CUE files.

No real media, sector payloads, original CUE or logs leave private workspace.
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

from tools.saturn_private_capture_session import (
    LOG_FILE, RECEIPT_FILE, capture_private,
)
from tools.verify_yabause_split_cue import make_split_fixture, MODE, EXPECTED


def invalid_cue_variants(original: bytes) -> dict[str, bytes]:
    assert original.startswith(b"CATALOG ") and b"TRACK 02 AUDIO" in original
    return {
        "unknown-directive": original.replace(
            b"INDEX 01 00:00:00", b"REM HIDDEN_CONTENT", 1),
        "extra-directive": original + b"REM EXTRA\n",
        "missing-catalog": b"REM TEST_ONLY\n" + original.split(b"\n", 1)[1],
        "duplicate-index": original.replace(
            b"INDEX 00 00:00:00\n", b"INDEX 00 00:00:00\nINDEX 00 00:00:00\n"),
        "missing-final-newline": original.rstrip(b"\r\n"),
        "oversized-quoted-name": original.replace(
            b'invented-track02.bin', b"Z" * 510 + b".bin"),
        "path-traversal": original.replace(
            b'invented-track02.bin', b"../test-audio.bin"),
        "wrong-audio-index": original.replace(
            b"INDEX 01 00:02:00", b"INDEX 01 00:01:00"),
        "extra-file": original + b'FILE "extra.bin" BINARY\n',
        "extra-trailing-token": original.replace(
            b"TRACK 02 AUDIO", b"TRACK 02 AUDIO garbage"),
        "different-track-mode": original.replace(
            b"TRACK 01 MODE1/2352", b"TRACK 01 MODE2/2352"),
        "nondigit-catalog": original.replace(
            b"CATALOG 0000000000000", b"CATALOG 0X00000000000"),
    }


def check_real_rejections(executable: Path, root: Path) -> dict:
    exe = executable.resolve(strict=True)
    if not exe.is_file() or not os.access(exe, os.X_OK):
        raise ValueError("expected runnable pinned real Yabause")
    if not root.is_absolute() or not root.is_dir() or any(root.iterdir()):
        raise ValueError("requires empty private workspace")
    pin = hashlib.sha256(exe.read_bytes()).hexdigest()
    original_dir = root / "template"
    original_dir.mkdir(mode=0o700)
    m, _ = make_split_fixture(original_dir)
    original = Path(m["files"]["cue"]).read_bytes()
    negatives = invalid_cue_variants(original)
    if len(negatives) != 12:
        raise ValueError("wrong number of negative controls")
    for label, altered in negatives.items():
        src = root / ("fixture-" + label)
        src.mkdir(mode=0o700)
        manifest, source_pins = make_split_fixture(src)
        cue = Path(manifest["files"]["cue"])
        cue.write_bytes(altered)
        source_pins["cue"] = (len(altered), hashlib.sha256(altered).hexdigest())
        output = root / ("test-" + label)
        output.mkdir(mode=0o700)
        try:
            capture_private(
                manifest, output, "menu_control",
                [str(exe), MODE, manifest["files"]["cue"]],
                pins=source_pins, seconds=15,
                expected_executable_sha256=pin,
            )
        except (ValueError, OSError):
            if (output / RECEIPT_FILE).exists() or (output / LOG_FILE).exists():
                raise ValueError("rejected CUE generated a success log/receipt")
        else:
            raise ValueError("original Yabause incorrectly accepted invalid CUE")
    return {
        "stage": 91,
        "actual_pinned_yabause_negative_processes": len(negatives),
        "strict_cue_negative_inputs_rejected": True,
        "no_fake_success_receipts": True,
        "historical_single_file_fallback_retained_by_workflow": True,
        "actual_game_media_used": False,
        "authentic_first_battle_execution_verified": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--executable", required=True, type=Path)
    args = ap.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix="vh-stage91-public-fixtures-") as temp:
            root = Path(temp)
            root.chmod(0o700)
            receipt = check_real_rejections(args.executable, root)
        print(json.dumps(receipt, sort_keys=True))
        print("STAGE91_REAL_PINNED_YABAUSE_STRICT_CUE_NEGATIVES_PASS")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        print("STAGE91_REAL_YABAUSE_CUE_NEGATIVE_REJECTED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
