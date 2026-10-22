#!/usr/bin/env python3
"""Stage98: locally run public pinned Yabause ISOCD callback on the *owned* disc.

A pass proves original two-file CUE/BIN open and selected sector reads through
the actual public Yabause ISOCD backend. It does NOT boot Saturn game code,
verify a screen, identify an active first battle or prove loader causality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from tools.saturn_private_boot_readiness import (
    audit_boot_readiness, _source_paths, _pinned_snapshot,
)
from tools.saturn_private_capture_session import _fingerprint, _not_in_checkout
from tools.patch_yabause_private_disc_probe import MODE, PASS

EXPECTED_ORIGINAL_FAD = (
    b"VHCD_FAD 150\n"
    b"VHCD_FAD 151\n"
    b"VHCD_FAD 166\n"
    b"VHCD_FAD 2479\n"
    b"VHCD_FAD 76486\n"
    b"VHCD_FAD 264652\n"
)
MAX_TIMEOUT = 120


def verify_local_original_iso_probe(
    runner: Path, cue: Path, track1: Path, track2: Path,
    workspace: Path, *, expected_runner_sha256: str,
    timeout: int = 50,
) -> dict:
    if (not isinstance(expected_runner_sha256, str) or
            re.fullmatch(r"[0-9a-f]{64}", expected_runner_sha256) is None):
        raise ValueError("independently obtained runner SHA-256 required")
    if type(timeout) is not int or not 1 <= timeout <= MAX_TIMEOUT:
        raise ValueError("unsafe runner duration")
    if (not workspace.is_absolute() or workspace.is_symlink() or
            not workspace.is_dir() or
            stat.S_IMODE(workspace.stat().st_mode) & 0o077 or
            any(workspace.iterdir())):
        raise ValueError("new empty 0700 local workspace required")
    _not_in_checkout(workspace)
    if (not runner.is_absolute() or runner.is_symlink() or
            not runner.is_file() or not os.access(runner, os.X_OK)):
        raise ValueError("absolute trusted local executable required")
    _not_in_checkout(runner)
    paths = _source_paths(cue, track1, track2)
    if workspace.resolve() in {path.parent.resolve() for path in paths.values()}:
        raise ValueError("private CUE and executable output must stay separate")
    runner_before = _fingerprint(runner)
    if runner_before[1] != expected_runner_sha256:
        raise ValueError("runner executable does not match pinned build digest")
    before = _pinned_snapshot(paths)
    ready = audit_boot_readiness(cue, track1, track2)
    if not ready["boot_ready_for_private_operator_validation"]:
        raise ValueError("Stage93 original source preflight failed")
    gate = workspace / "control.gate"
    log = workspace / "fad.vhcdlog"
    env = dict(os.environ)
    env.update({
        "VH_SATURN_CAPTURE_GATE": str(gate),
        "VH_SATURN_FAD_LOG": str(log),
        "HOME": str(workspace),
    })
    try:
        process = subprocess.run(
            [str(runner), MODE, str(cue)],
            cwd=workspace, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=timeout, check=False, start_new_session=True, umask=0o077,
        )
        if (process.returncode != 0 or
                PASS not in process.stdout.decode("utf-8", "replace").splitlines()):
            raise ValueError("genuine Yabause ISOCD probe failed")
        if ({p.name for p in workspace.iterdir()} != {log.name} or
                gate.exists() or log.is_symlink() or
                not stat.S_ISREG(log.lstat().st_mode) or
                stat.S_IMODE(log.stat().st_mode) & 0o077 or
                log.read_bytes() != EXPECTED_ORIGINAL_FAD):
            raise ValueError("real original-disc physical sector trace differs")
        after = _pinned_snapshot(paths)
        if before != after or runner_before != _fingerprint(runner):
            raise ValueError("source or binary mutated during real ISO backend probe")
        receipt = {
            "schema_version": 1,
            "kind": "STAGE98_PRIVATE_ORIGINAL_CUE_ISOCD_READ_ONLY_WITNESS",
            "original_track1_track2_cue_stage02_hashes_stable": True,
            "real_pinned_public_yabause_binary_hash_stable": True,
            "exact_original_cue_path_opened_in_iso_cd_backend": True,
            "physical_fad_events_read_through_real_iso_cd": 6,
            "saturn_boot_and_iso9660_pvd_read_through_iso_cd": True,
            "stage02_candidate_fad_addresses_read": 2,
            "first_audio_track_fad_read": True,
            "real_game_code_executed": False,
            "original_first_battle_screen_observed": False,
            "source_loader_to_map_verified": False,
            "live_frame_fad_synchronization_verified": False,
            "original_disc_data_exported": False,
        }
        path = workspace / "private-probe-receipt.json"
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(receipt, out, sort_keys=True, indent=2)
            out.write("\n")
        return receipt
    except Exception:
        # Numeric-only local FAD is retained for private diagnosis; no
        # success receipt is generated on failure or cancelled process.
        raise


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runner", required=True, type=Path)
    p.add_argument("--runner-sha256", required=True)
    p.add_argument("--cue", required=True, type=Path)
    p.add_argument("--track1", required=True, type=Path)
    p.add_argument("--track2", required=True, type=Path)
    p.add_argument("--private-dir", required=True, type=Path)
    args = p.parse_args()
    try:
        receipt = verify_local_original_iso_probe(
            args.runner, args.cue, args.track1, args.track2, args.private_dir,
            expected_runner_sha256=args.runner_sha256,
        )
    except (OSError, ValueError, TypeError, UnicodeError, subprocess.SubprocessError):
        print("STAGE98_PRIVATE_REAL_YABAUSE_ISO_PROBE_REJECTED", file=sys.stderr)
        return 1
    print("STAGE98_PRIVATE_REAL_YABAUSE_ISO_BACKEND_PASS "
          f"fad_events={receipt['physical_fad_events_read_through_real_iso_cd']} "
          "original_game_boot=false first_battle_observed=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
