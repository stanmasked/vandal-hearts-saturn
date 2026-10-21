#!/usr/bin/env python3
"""Stage95: private four-capture menu/battle cohort with strict trace provenance.

Consumes only local Stage94 capture folders; no emulator is launched by this
auditor. Two menu and two first-battle *operator-declared* sessions are needed.
Even a passing cohort does NOT establish actual independent cold boots, game
frames, a game loader or first-battle authenticity.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import stat
import sys

from tools.saturn_private_boot_handoff import HANDOFF_RECEIPT
from tools.saturn_private_capture_session import (
    PINNED, LOG_FILE, RECEIPT_FILE, _not_in_checkout,
)
from tools.saturn_yabause_fad_log import MAX_LOG_BYTES, build_private_trace, parse_fad_log

PHASES = {"menu_control", "first_battle_entry"}
SESSION_ID = re.compile(r"[0-9a-f]{32}\Z")
EXPECTED_DIR_FILES = {HANDOFF_RECEIPT, RECEIPT_FILE, LOG_FILE}
MAX_RECEIPT = 8192


def _private_directory(path: Path) -> None:
    if not isinstance(path, Path) or not path.is_absolute() or path.is_symlink():
        raise ValueError("absolute nonsymlinked private directory required")
    _not_in_checkout(path)
    if not path.is_dir() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("directory is not protected 0700")
    if path.stat().st_nlink < 1:
        raise ValueError("invalid private directory")


def _private_regular(path: Path, maximum: int) -> bytes:
    state = path.lstat()
    if (not stat.S_ISREG(state.st_mode) or state.st_nlink != 1 or
            stat.S_IMODE(state.st_mode) & 0o077 or
            state.st_size < 1 or state.st_size > maximum):
        raise ValueError("unsafe, leaked or oversized private capture file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size) != (
                state.st_dev, state.st_ino, state.st_size):
            raise ValueError("capture file changed during open")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            content = stream.read(maximum + 1)
        after = os.fstat(fd)
        if (len(content) > maximum or len(content) != before.st_size or
                (before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError("capture file mutated during read")
        return content
    finally:
        os.close(fd)


def _json_receipt(path: Path) -> dict:
    raw = _private_regular(path, MAX_RECEIPT)
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("malformed private receipt") from exc
    if not isinstance(result, dict) or type(result.get("schema_version")) is not int or result["schema_version"] != 1:
        raise ValueError("invalid private receipt schema")
    return result


def audit_four_capture_cohort(
    sessions: list[tuple[str, Path]], *,
    track1_sectors: int | None = None,
) -> tuple[dict, dict]:
    if (not isinstance(sessions, list) or len(sessions) != 4 or
            any(not isinstance(item, tuple) or len(item) != 2 for item in sessions)):
        raise ValueError("exactly four operator-labeled private sessions required")
    sectors = PINNED["track1"][0] // 2352 if track1_sectors is None else track1_sectors
    seen_directories = set()
    seen_file_ids = set()
    seen_sessions = set()
    phase_counts = Counter()
    phase_raw = {"menu_control": [], "first_battle_entry": []}
    phase_logs = []
    for phase, directory in sessions:
        if phase not in PHASES:
            raise ValueError("unrecognized capture phase")
        _private_directory(directory)
        key = (directory.stat().st_dev, directory.stat().st_ino)
        if key in seen_directories:
            raise ValueError("reused capture directory")
        seen_directories.add(key)
        if {p.name for p in directory.iterdir()} != EXPECTED_DIR_FILES:
            raise ValueError("unexpected or missing private capture file")
        for filename in EXPECTED_DIR_FILES:
            path = directory / filename
            identity = (path.lstat().st_dev, path.lstat().st_ino)
            if identity in seen_file_ids:
                raise ValueError("file reused between capture workspaces")
            seen_file_ids.add(identity)
        receipt = _json_receipt(directory / HANDOFF_RECEIPT)
        capture = _json_receipt(directory / RECEIPT_FILE)
        if (receipt.get("kind") != "STAGE94_PRIVATE_SOURCE_TO_CAPTURE_INTEGRITY_ONLY" or
                capture.get("kind") != "PRIVATE_SATURN_FAD_CAPTURE_INTEGRITY_ONLY"):
            raise ValueError("expected completed Stage94 + Stage86 receipt pair")
        for name in (
            "full_stage02_disc_preflight_before_and_after",
            "private_media_identity_stable_during_handoff",
            "declared_executable_sha256_matched_before_and_after",
            "exact_declared_cue_argument",
        ):
            if receipt.get(name) is not True:
                raise ValueError("incomplete source/runner integrity")
        for name in (
            "pinned_english_v1_1_track1_track2_cue_match",
            "pinned_files_unchanged_after_run",
            "manual_gate_closed_at_exit",
            "runner_matches_separately_supplied_sha256",
            "cue_path_exactly_present_in_command",
        ):
            if capture.get(name) is not True:
                raise ValueError("incomplete capture integrity")
        for name in (
            "original_saturn_game_boot_verified",
            "observed_frame_to_fad_sync_verified",
            "original_first_battle_screen_verified",
        ):
            if receipt.get(name) is not False:
                raise ValueError("higher-level scene truth must not be invented")
        if capture.get("scene_frame_synchronized_verified") is not False:
            raise ValueError("phase statement is not frame evidence")
        if capture.get("phase_operator_declared") != phase:
            raise ValueError("capture phase differs from operator declaration")
        session_id = capture.get("session_id")
        if not isinstance(session_id, str) or not SESSION_ID.fullmatch(session_id) or session_id in seen_sessions:
            raise ValueError("invalid or reused private session ID")
        seen_sessions.add(session_id)
        raw = _private_regular(directory / LOG_FILE, MAX_LOG_BYTES)
        if not raw.endswith(b"\n") or b"\r" in raw:
            raise ValueError("noncanonical log line endings")
        try:
            parsed = parse_fad_log(raw.decode("ascii"))
        except UnicodeError as exc:
            raise ValueError("nonnumeric capture content") from exc
        count = len(parsed)
        if (type(receipt.get("numeric_only_fad_event_count")) is not int or
                type(capture.get("numeric_fad_events")) is not int or
                receipt["numeric_only_fad_event_count"] != count or
                capture["numeric_fad_events"] != count):
            raise ValueError("numeric log count not bound to both receipts")
        phase_counts[phase] += 1
        phase_raw[phase].append(raw)
        phase_logs.append((phase, raw.decode("ascii")))
    if phase_counts != {"menu_control": 2, "first_battle_entry": 2}:
        raise ValueError("two menu controls and two battle-entry declarations required")
    # The converter explicitly bounds each FAD to DATA Track 1 (offset 150).
    # Invalid CDDA reads must not accidentally shift into an ISO data LBA.
    trace = build_private_trace(sectors, phase_logs)
    duplicate_pairs = {
        phase: int(raws[0] == raws[1]) for phase, raws in phase_raw.items()
    }
    summary = {
        "schema_version": 1,
        "kind": "STAGE95_PRIVATE_FOUR_CAPTURE_COHORT_INTEGRITY_ONLY",
        "validated_stage94_capture_workspaces": 4,
        "declared_menu_sessions": 2,
        "declared_battle_entry_sessions": 2,
        "distinct_capture_directories": 4,
        "distinct_self_reported_session_ids": 4,
        "all_source_and_runner_receipts_consistent": True,
        "all_numeric_log_counts_match_receipts": True,
        "iso_track1_fad_to_lba_conversion_succeeded": True,
        "identical_numeric_trace_pairs_by_phase": duplicate_pairs,
        "identical_deterministic_reads_are_not_rejected": True,
        "actual_independent_emulator_processes_verified": False,
        "actual_cold_boots_verified": False,
        "original_game_boot_observed": False,
        "original_first_battle_screen_observed": False,
        "frame_to_fad_synchronization_verified": False,
        "source_loader_to_map_relationship_verified": False,
        "original_media_bytes_exported": False,
    }
    return summary, trace


def _write_private_json(path: Path, obj: dict):
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError("private output paths must be absolute")
    _private_directory(path.parent)
    if path.exists() or path.is_symlink():
        raise ValueError("refusing to replace private output")
    data = (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--menu-dir", action="append", type=Path, required=True)
    p.add_argument("--battle-dir", action="append", type=Path, required=True)
    p.add_argument("--summary", type=Path, required=True)
    p.add_argument("--private-trace", type=Path, required=True)
    args = p.parse_args()
    created = []
    try:
        sources = ([("menu_control", x) for x in args.menu_dir] +
                   [("first_battle_entry", x) for x in args.battle_dir])
        if (args.summary.resolve() == args.private_trace.resolve() or
                args.summary.parent.resolve() != args.private_trace.parent.resolve() or
                args.summary.parent.resolve() in
                {x.resolve() for _, x in sources}):
            raise ValueError("summary and trace outputs must be distinct in a separate private folder")
        summary, trace = audit_four_capture_cohort(sources)
        for output, obj in ((args.private_trace, trace), (args.summary, summary)):
            _write_private_json(output, obj)
            created.append(output)
    except (OSError, ValueError, TypeError, KeyError):
        for path in created:
            try:
                path.unlink()
            except OSError:
                pass
        print("STAGE95_PRIVATE_FOUR_CAPTURE_COHORT_REJECTED", file=sys.stderr)
        return 1
    print("STAGE95_PRIVATE_CAPTURE_COHORT_INTEGRITY_PASS "
          "observed_first_battle=false independent_sessions_verified=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
