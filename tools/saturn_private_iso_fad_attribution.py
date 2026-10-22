#!/usr/bin/env python3
"""Stage100: match real gated FAD observations to private Saturn ISO9660 extents.

This is an address-intersection tool, NOT proof a particular original
gameplay scene was visible, or that each CD read came from a game loader.
No original track, sector payload, frame image or log is copied to GitHub.
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

from tools.saturn_iso import SaturnISO
from tools.saturn_private_boot_readiness import (
    STAGE02_ISO, STAGE02_RESOURCE_NAMES, _pinned_snapshot, _source_paths,
    audit_boot_readiness,
)
from tools.saturn_private_capture_cohort import _private_directory, _private_regular
from tools.saturn_private_split_cue_preflight import inspect_cue
from tools.saturn_private_capture_session import PINNED

MAX_LOG_BYTES = 4 * 1024 * 1024
LINE = re.compile(rb"VHCD_FAD (0|[1-9][0-9]*)\Z")
SUMMARY_KIND = "STAGE100_PRIVATE_ORIGINAL_GAME_FAD_FILE_EXTENT_OVERLAP_ONLY"
PRIVATE_REPORT = "fad-file-overlap.json"


def parse_numeric_gated_fad_log(path: Path) -> list[int]:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError("absolute private log required")
    _private_directory(path.parent)
    payload = _private_regular(path, MAX_LOG_BYTES)
    if not payload.endswith(b"\n") or b"\r" in payload or b"\x00" in payload:
        raise ValueError("unexpected numeric FAD framing")
    events = []
    for line in payload.splitlines():
        m = LINE.fullmatch(line)
        if m is None:
            raise ValueError("noncanonical CD callback entry")
        value = int(m.group(1))
        if value >= 0x100000000:
            raise ValueError("unrepresentable physical Saturn FAD")
        events.append(value)
    if not events:
        raise ValueError("empty CD callback log")
    return events


def attribute_fad_events(
    events: list[int],
    file_entries: list[dict],
    *,
    data_sector_count: int,
    audio_index01_fad: int,
    leadout_fad: int,
) -> dict:
    if (not isinstance(events, list) or not events or
            any(type(x) is not int or x < 150 or x >= leadout_fad for x in events) or
            type(data_sector_count) is not int or data_sector_count <= 0 or
            not 150 + data_sector_count <= audio_index01_fad < leadout_fad):
        raise ValueError("invalid disc geometry or out-of-disc FAD")
    if not isinstance(file_entries, list):
        raise ValueError("invalid ISO9660 file inventory")

    # A sector may legally be outside any file, or be shared by extents.
    # Never invent a unique owner for an overlapping ISO9660 extent.
    intervals = []
    names = set()
    for entry in file_entries:
        name, lba, length = (
            entry.get("name"), entry.get("lba"), entry.get("bytes")
        )
        if (not isinstance(name, str) or not name or name in names or
                type(lba) is not int or type(length) is not int or
                lba < 0 or length < 0 or
                lba + (length + 2047) // 2048 > data_sector_count):
            raise ValueError("invalid or ambiguous ISO entry")
        names.add(name)
        if length:
            intervals.append((150 + lba, 150 + lba + (length + 2047)//2048 - 1, name))

    file_hits = Counter()
    file_unique_fad = {}
    unlabeled_events = audio_events = pregap_events = multi_owner_events = 0
    all_fad_counts = Counter(events)
    for fad, repetitions in all_fad_counts.items():
        if 150 <= fad < 150 + data_sector_count:
            owners = [name for first, last, name in intervals if first <= fad <= last]
            if not owners:
                unlabeled_events += repetitions
            else:
                if len(owners) > 1:
                    multi_owner_events += repetitions
                for name in owners:
                    file_hits[name] += repetitions
                    file_unique_fad.setdefault(name, set()).add(fad)
        elif audio_index01_fad <= fad < leadout_fad:
            audio_events += repetitions
        else:
            pregap_events += repetitions

    # Stage02's two initial first-battle resource candidates are explicit
    # claims made from inventory names, NOT assumed gameplay-loaded scenes.
    candidate_names = ("BATL1PRG.BIN", "MAP_1_1C.BIN")
    candidate_hits = {name: file_hits[name] for name in candidate_names}
    file_details = [
        {
            "name": name,
            "event_count": file_hits[name],
            "distinct_fad_count": len(file_unique_fad[name]),
        }
        for name in sorted(file_hits)
    ]
    summary = {
        "schema_version": 1,
        "kind": SUMMARY_KIND,
        "numeric_callback_fad_events": len(events),
        "unique_physical_fads": len(all_fad_counts),
        "events_in_named_file_extents": sum(
            repetitions for fad, repetitions in all_fad_counts.items()
            if 150 <= fad < 150 + data_sector_count and
            any(first <= fad <= last for first, last, _ in intervals)
        ),
        "events_outside_named_file_extents": unlabeled_events,
        "events_in_cd_audio": audio_events,
        "events_between_data_and_audio_index": pregap_events,
        "events_with_multiple_possible_file_owners": multi_owner_events,
        "distinct_named_files_touched": len(file_hits),
        "candidate_battle_resource_hits": candidate_hits,
        "original_game_scene_or_first_battle_verified": False,
        "frame_to_fad_callback_synchronization_verified": False,
        "actual_game_loader_causality_verified": False,
        "game_resource_bytes_exported": False,
    }
    return {"summary": summary, "private_file_details": file_details}


def audit_private_original_fad_files(
    cue: Path, track1: Path, track2: Path, log: Path, *,
    expected_iso: dict | None = None,
    expected_resources: frozenset[str] | None = None,
) -> dict:
    paths = _source_paths(cue, track1, track2)
    before = _pinned_snapshot(paths)
    try:
        ready = audit_boot_readiness(
            cue, track1, track2, expected_iso=expected_iso,
            expected_resources=expected_resources,
        )
        if not ready["boot_ready_for_private_operator_validation"]:
            raise ValueError("all-three-private-source readiness absent")
        actual_log = parse_numeric_gated_fad_log(log)
        info = inspect_cue(
            cue.read_bytes(),
            track1_bytes=PINNED["track1"][0],
            track2_bytes=PINNED["track2"][0],
        )
        inventory = SaturnISO(track1).inspect(include_files=True)
        report = attribute_fad_events(
            actual_log, inventory["file_entries"],
            data_sector_count=inventory["sectors"],
            audio_index01_fad=info["audio_index01_fad"],
            leadout_fad=info["leadout_fad"],
        )
    finally:
        after = _pinned_snapshot(paths)
        if before != after:
            raise ValueError("source changed during FAD-to-file attribution")
    return report


def write_private_attribution_report(directory: Path, report: dict) -> Path:
    _private_directory(directory)
    output = directory / PRIVATE_REPORT
    if output.exists() or output.is_symlink():
        raise ValueError("will not replace an existing private report")
    data = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return output


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cue", type=Path, required=True)
    p.add_argument("--track1", type=Path, required=True)
    p.add_argument("--track2", type=Path, required=True)
    p.add_argument("--fad-log", type=Path, required=True)
    p.add_argument("--private-output-dir", type=Path, required=True)
    a = p.parse_args()
    try:
        result = audit_private_original_fad_files(
            a.cue, a.track1, a.track2, a.fad_log
        )
        write_private_attribution_report(a.private_output_dir, result)
    except (ValueError, OSError, TypeError, UnicodeError, KeyError):
        print("STAGE100_PRIVATE_FAD_TO_ISO_FILES_REJECTED", file=sys.stderr)
        return 1
    # No filenames, track hashes, source paths, frame pixels or private FAD
    # values printed; the full overlap report stays in local 0600 JSON.
    summary = result["summary"]
    print(
        "STAGE100_PRIVATE_FAD_FILE_OVERLAP_PASS "
        f"events={summary['numeric_callback_fad_events']} "
        f"distinct_files={summary['distinct_named_files_touched']} "
        "first_battle_verified=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
