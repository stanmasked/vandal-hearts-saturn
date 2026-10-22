#!/usr/bin/env python3
"""Stage98 CI: actual pinned Yabause opens invented split CUE, reads real files."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from tools.verify_yabause_split_cue import make_split_fixture
from tools.patch_yabause_private_disc_probe import PASS, MODE

FAKE_FADS = b"VHCD_FAD 150\nVHCD_FAD 151\nVHCD_FAD 302\n"


def test_real_probe(executable: Path) -> dict:
    runner = executable.resolve(strict=True)
    if not runner.is_file() or not os.access(runner, os.X_OK):
        raise ValueError("missing genuine public Yabause executable")
    with tempfile.TemporaryDirectory(prefix="vh-stage98-invented-") as td:
        root = Path(td)
        root.chmod(0o700)
        source = root / "tiny-fixture"
        source.mkdir(mode=0o700)
        manifest, _ = make_split_fixture(source)
        data = Path(manifest["files"]["track1"])
        raw = bytearray(data.read_bytes())
        raw[16:31] = b"SEGA SEGASATURN"
        data.write_bytes(raw)
        good = root / "good"
        good.mkdir(mode=0o700)
        log = good / "fad.vhcdlog"
        gate = good / "gate"
        env = dict(os.environ)
        env.update(VH_SATURN_CAPTURE_GATE=str(gate),
                   VH_SATURN_FAD_LOG=str(log), HOME=str(good))
        cp = subprocess.run([str(runner), MODE, manifest["files"]["cue"]],
                            cwd=good, env=env, capture_output=True,
                            timeout=25, check=False)
        if (cp.returncode != 0 or
                cp.stdout.decode("utf-8", "replace").splitlines() != [PASS] or
                log.read_bytes() != FAKE_FADS or gate.exists()):
            raise ValueError("real public Yabause did not read synthetic split CUE")

        # Negative control: ensure the real callback really validates
        # Saturn boot payload, not merely the presence of a CUE argv.
        bad = root / "bad"
        bad.mkdir(mode=0o700)
        raw[16:31] = b"NOT_SATURN_BOOT"
        data.write_bytes(raw)
        env.update(VH_SATURN_CAPTURE_GATE=str(bad / "gate"),
                   VH_SATURN_FAD_LOG=str(bad / "fad.vhcdlog"),
                   HOME=str(bad))
        denied = subprocess.run(
            [str(runner), MODE, manifest["files"]["cue"]],
            cwd=bad, env=env, capture_output=True, timeout=25, check=False)
        if denied.returncode == 0 or PASS.encode() in denied.stdout:
            raise ValueError("real Yabause accepted corrupted synthetic boot magic")
        return {
            "stage": 98,
            "genuine_pinned_public_yabause_iso_backend_exercised": True,
            "actual_split_cue_and_two_fabricated_bin_files_opened": True,
            "expected_fake_fad_events": 3,
            "negative_corrupt_boot_sector_rejected": True,
            "original_game_media_used": False,
            "gameplay_frame_or_first_battle_verified": False,
        }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--executable", required=True, type=Path)
    args = p.parse_args()
    try:
        receipt = test_real_probe(args.executable)
    except (OSError, ValueError, subprocess.SubprocessError):
        print("STAGE98_REAL_YABAUSE_FAKE_DISC_PROBE_REJECTED", file=sys.stderr)
        return 1
    if receipt["expected_fake_fad_events"] == 3:
        print("STAGE98_REAL_YABAUSE_FAKE_SPLIT_CUE_PROBE_PASS")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
