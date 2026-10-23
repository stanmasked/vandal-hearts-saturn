"""Stage130: fresh private paired recapture with preservation-gated handoff.

This entrypoint is private-host only. Public CI must mock original-game work.
It neither recovers the historical archive nor certifies Drive permissions.
"""
from __future__ import annotations
from pathlib import Path
import shutil

from tools.saturn_private_stage130_storage_preflight import verify_new_capture_storage
from tools.saturn_private_capture_archive_gate import _private_fingerprint
from tools.saturn_private_capture_packager import package_stage124_style_pair
from tools.saturn_private_archived_pair_audit import audit_archived_stage124_pair
from tools.saturn_private_drive_roundtrip import private_archive_roundtrip
from tools.saturn_private_prologue_continue_ninth_c import run_private_prologue_continue_ninth_c


def recapture_with_durable_handoff(cue: Path, track1: Path, track2: Path,
                                  runner: Path, expected_runner_sha256: str,
                                  control: Path, enabled: Path, archive: Path,
                                  remote_object: str, readback: Path) -> dict:
    verify_new_capture_storage(control, enabled, archive, readback, remote_object)
    if not shutil.which("rclone"):
        raise ValueError("private rclone installation required before original run")
    run = run_private_prologue_continue_ninth_c(
        cue, track1, track2, runner, expected_runner_sha256, control, enabled)
    if (run.get("checkpoint_png_count_per_process") != 900
            or run.get("first_battle_or_player_control_verified") is not False):
        raise ValueError("private Stage124 pair integrity unconfirmed")
    packaged = package_stage124_style_pair(control, enabled, archive)
    if (packaged.get("stage124_paired_capture_audit_executed") is not True
            or packaged.get("regular_members") != 1816
            or packaged.get("historical_stage124_archive_recovered") is not False):
        raise ValueError("private capture packaging did not pass audit")
    before = _private_fingerprint(archive)
    transferred = private_archive_roundtrip(
        archive, remote_object, readback,
        expected_size=before[0], expected_sha256=before[1])
    if (transferred.get("configured_remote_roundtrip_verified") is not True
            or transferred.get("stage125_drive_receipt_issued") is not False
            or transferred.get("google_drive_owner_only_verified") is not False):
        raise ValueError("separate private readback not completed")
    semantic = audit_archived_stage124_pair(
        readback, expected_size=before[0], expected_sha256=before[1])
    if semantic.get("stage124_paired_capture_semantics_verified_in_archive") is not True:
        raise ValueError("downloaded Stage124 paired capture audit failed")
    if _private_fingerprint(archive) != before:
        raise ValueError("private local archive mutated during handoff")
    # Do not delete or overwrite the raw captures, disc, archive, or readback.
    # Do not issue Stage125 receipt until authenticated Drive ACL is checked.
    return {"stage": 130, "fresh_recapture_handoff_passed": True,
            "raw_capture_outputs_preserved": True,
            "historical_stage124_archive_recovered": False,
            "owner_only_drive_acl_verified": False,
            "stage125_receipt_issued": False,
            "original_tactical_gameplay_verified": False}
