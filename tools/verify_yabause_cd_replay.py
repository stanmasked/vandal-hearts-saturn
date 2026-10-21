#!/usr/bin/env python3
"""Stage85: audit two independent runs of the real Yabause synthetic ISO smoke.

Every input sector is invented, no game/BIOS/private file is read. Runs an
already-compiled pinned Yabause runner under a deliberately minimal
environment and compares both the capture and 4-KiB source image by SHA-256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

SUCCESS = "STAGE84_REAL_YABAUSE_SYNTHETIC_ISO_CD_PASS"
EXPECTED_TRACE = b"VHCD_FAD 150\nVHCD_FAD 151\n"
EXPECTED_SOURCE = bytes(
    (((i // 2048) * 33 + i * 11 + 7) & 0xFF) for i in range(4096)
)
SOURCE_NAME = "vh_created_iso_fixture.iso"
LOG_NAME = "real-iso.vhcdlog"
GATE_NAME = "control.gate"
CHILD_FILES = {SOURCE_NAME, LOG_NAME}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_trial(workdir: Path, output: str) -> dict[str, str | int]:
    if not workdir.is_dir() or not isinstance(output, str):
        raise ValueError("invalid trial workspace or stdout")
    if output.splitlines().count(SUCCESS) != 1:
        raise ValueError("missing or duplicated real-process success receipt")
    # The gate must have been removed, and the temporary directory must
    # contain nothing beyond the invented 4KiB fixture and numeric trace.
    actual = {item.name for item in workdir.iterdir()}
    if actual != CHILD_FILES:
        raise ValueError("unexpected/missing files in isolated trial")
    source = workdir / SOURCE_NAME
    trace = workdir / LOG_NAME
    if not source.is_file() or source.is_symlink() or not trace.is_file() or trace.is_symlink():
        raise ValueError("missing or redirected output")
    original = source.read_bytes()
    recorded = trace.read_bytes()
    if original != EXPECTED_SOURCE:
        raise ValueError("synthetic source content changed")
    if recorded != EXPECTED_TRACE:
        raise ValueError("incorrect, extra or leaked sector receipt")
    return {
        "source_sha256": sha256(original),
        "trace_sha256": sha256(recorded),
        "source_bytes": len(original),
        "trace_bytes": len(recorded),
    }


def execute_trial(executable: Path, workspace: Path, label: str) -> dict[str, str | int]:
    child = workspace / label
    child.mkdir(mode=0o700)
    env = {
        "HOME": str(child),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C",
        "VH_SATURN_CAPTURE_GATE": str(child / GATE_NAME),
        "VH_SATURN_FAD_LOG": str(child / LOG_NAME),
    }
    try:
        result = subprocess.run(
            [str(executable), "vh-synthetic-iso-read"],
            cwd=child, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Yabause synthetic test timed out") from exc
    if result.returncode != 0:
        raise ValueError("Yabause synthetic test returned nonzero status")
    return verify_trial(child, result.stdout)


def audit_repeated_runs(executable: Path, workspace: Path) -> dict:
    exe = executable.resolve(strict=True)
    if not exe.is_file() or not os.access(exe, os.X_OK):
        raise ValueError("runner is not executable")
    if not workspace.is_dir() or any(workspace.iterdir()):
        raise ValueError("fresh empty workspace required")
    first = execute_trial(exe, workspace, "run-one")
    second = execute_trial(exe, workspace, "run-two")
    if first != second:
        raise ValueError("independent run digests or byte counts diverged")
    return {
        "stage": 85,
        "actual_independent_processes": 2,
        "public_pinned_runner_verified_by_ci": True,
        "synthetic_only": True,
        "private_game_media_used": False,
        "source_sha256": first["source_sha256"],
        "fad_log_sha256": first["trace_sha256"],
        "record_count_per_run": 2,
        "matches_between_runs": True,
        "authentic_game_boot_observed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = audit_repeated_runs(args.executable, args.workspace)
        print(json.dumps(receipt, sort_keys=True))
        print("STAGE85_TWO_ISOLATED_REAL_YABAUSE_ISO_REPLAYS_PASS")
        return 0
    except (ValueError, OSError) as exc:
        print("STAGE85_REPLAY_REJECTED " + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
