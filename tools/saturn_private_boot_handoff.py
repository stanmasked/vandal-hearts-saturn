#!/usr/bin/env python3
"""Stage94: private Saturn preflight -> gated runner -> postflight, fail closed.

A successful receipt only means the locally supplied media, declared
executable, and numeric-only trace passed their independent checks.
It does NOT prove original game boot, a scene, CD use or authenticity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import stat
import sys

from tools.saturn_private_boot_readiness import (
    audit_boot_readiness, _write_receipt,
)
from tools.saturn_private_capture_session import (
    PINNED, LOG_FILE, RECEIPT_FILE, _fingerprint, _not_in_checkout,
    _private_empty_dir, capture_private,
)

HANDOFF_RECEIPT = "source-to-capture-receipt.json"
HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def run_private_handoff(
    cue: Path, track1: Path, track2: Path, workspace: Path,
    phase: str, command: list[str], runner_pin: str, *,
    seconds: int = 1800,
    expected_iso: dict | None = None,
    expected_resources: frozenset[str] | None = None,
    pins: dict | None = None,
) -> dict:
    """Wrap already validated tools; no copying or extraction of media.

    expected_iso/resources/pins overrides are for fake-only unit tests.
    CLI always uses the immutable Stage02 original-disc pins.
    """
    if not isinstance(runner_pin, str) or not HEX_SHA256.fullmatch(runner_pin):
        raise ValueError("expected separately pinned SHA-256 for runner")
    if not isinstance(command, list) or not command or not isinstance(command[0], str):
        raise ValueError("executable path and arguments required")
    paths = (cue, track1, track2)
    if any(not isinstance(p, Path) or not p.is_absolute() for p in paths):
        raise ValueError("all private media paths must be absolute")
    if (not Path(command[0]).is_absolute() or
            str(cue) not in command[1:]):
        raise ValueError("exact absolute CUE must be a full runner argv token")
    if not 1 <= seconds <= 18000:
        raise ValueError("invalid bounded session duration")
    if pins is not None and pins != PINNED:
        raise ValueError("pin override must match test-patched global pins")
    _private_empty_dir(workspace)
    runner_before = _fingerprint(Path(command[0]))
    if runner_before[1] != runner_pin:
        raise ValueError("runner differs from separately supplied pin")

    before = audit_boot_readiness(
        cue, track1, track2, expected_iso=expected_iso,
        expected_resources=expected_resources,
    )
    if not before["boot_ready_for_private_operator_validation"]:
        raise ValueError("preflight not ready")

    # The Stage86/87 wrapper independently verifies all source bytes before
    # and after running and demands a closed gate and numeric-only FAD log.
    manifest = {
        "schema_version": 1,
        "product_code": "T-9526G",
        "release_kind": "translation_patched",
        "files": {
            "cue": str(cue), "track1": str(track1), "track2": str(track2),
        },
    }
    capture = capture_private(
        manifest, workspace, phase, command, seconds=seconds,
        pins=PINNED, expected_executable_sha256=runner_pin,
    )
    try:
        after = audit_boot_readiness(
            cue, track1, track2, expected_iso=expected_iso,
            expected_resources=expected_resources,
        )
        if before != after:
            raise ValueError("boot format readiness changed between checks")
        if runner_before != _fingerprint(Path(command[0])):
            raise ValueError("runner changed after second source inspection")
        if {x.name for x in workspace.iterdir()} != {LOG_FILE, RECEIPT_FILE}:
            raise ValueError("unexpected capture outputs")
        if (not capture["pinned_files_unchanged_after_run"] or
                not capture["runner_matches_separately_supplied_sha256"] or
                not capture["cue_path_exactly_present_in_command"] or
                capture["numeric_fad_events"] <= 0):
            raise ValueError("incomplete private capture receipt")

        combined = {
            "schema_version": 1,
            "kind": "STAGE94_PRIVATE_SOURCE_TO_CAPTURE_INTEGRITY_ONLY",
            "full_stage02_disc_preflight_before_and_after": True,
            "private_media_identity_stable_during_handoff": True,
            "declared_executable_sha256_matched_before_and_after": True,
            "exact_declared_cue_argument": True,
            "numeric_only_fad_event_count": capture["numeric_fad_events"],
            "stage86_private_capture_receipt_exists": True,
            "complete_source_ready_for_manual_gameplay_inspection": True,
            "original_saturn_game_boot_verified": False,
            "game_disc_actually_opened_independently_verified": False,
            "original_first_battle_screen_verified": False,
            "source_loader_to_map_relationship_verified": False,
            "observed_frame_to_fad_sync_verified": False,
            "independent_capture_sessions_verified": False,
            "japanese_master_equivalence_verified": False,
            "original_media_bytes_exported": False,
        }
        _write_receipt(workspace / HANDOFF_RECEIPT, combined)
        return combined
    except Exception:
        # Stage86 may have issued its lower-assurance success receipt before
        # the *subsequent* Stage93 integrity check failed. Revoke it rather
        # than leaving behind a misleading positive result.
        old = workspace / RECEIPT_FILE
        if old.exists() and old.is_file() and not old.is_symlink():
            old.unlink()
        raise


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cue", type=Path, required=True)
    p.add_argument("--track1", type=Path, required=True)
    p.add_argument("--track2", type=Path, required=True)
    p.add_argument("--private-dir", type=Path, required=True)
    p.add_argument("--phase", required=True, choices=["menu_control", "first_battle_entry"])
    p.add_argument("--runner-sha256", required=True)
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("command", nargs=argparse.REMAINDER)
    args = p.parse_args()
    try:
        if not args.command or args.command[0] != "--":
            raise ValueError("runner command must be after --")
        run_private_handoff(
            args.cue, args.track1, args.track2, args.private_dir,
            args.phase, args.command[1:], args.runner_sha256,
            seconds=args.timeout,
        )
    except (ValueError, OSError, TypeError, KeyError):
        print("STAGE94_PRIVATE_BOOT_HANDOFF_REJECTED", file=sys.stderr)
        return 1
    print("STAGE94_PRIVATE_INTEGRITY_HANDOFF_PASS "
          "original_game_boot_verified=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
