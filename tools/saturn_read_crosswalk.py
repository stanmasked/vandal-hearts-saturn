#!/usr/bin/env python3
"""Stage73: compare private Saturn ISO sector-read traces against ISO9660 extents.

Inputs are metadata-only (file names, extents and read LBAs). This module
never opens the Saturn disc or exports the original game contents. Correlation
of a sector read with an extent is a *candidate*, NOT runtime loader proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.saturn_resource_candidates import CANDIDATE_GROUPS

USER_SECTOR_BYTES = 2048
MAX_FILES = 20000
MAX_RUNS = 64
MAX_EVENTS_PER_RUN = 20000
MAX_LBA = 20_000_000
MAX_ISO_FILE_BYTES = 0xffffffff  # ISO9660 both-endian 32-bit file size
ADDRESSING = "iso9660_logical_data_lba"
PHASES = {"first_battle_entry", "menu_control"}
CANDIDATES = tuple(
    name for _, names, _ in CANDIDATE_GROUPS for name in names
)


def _nonnegative(value, name, upper=MAX_LBA):
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= upper:
        raise ValueError("invalid numeric " + name)
    return value


def _validate_inventory(document):
    if not isinstance(document, dict) or not isinstance(document.get("file_entries"), list):
        raise ValueError("expected ISO9660 file_entries metadata")
    entries = document["file_entries"]
    if len(entries) > MAX_FILES:
        raise ValueError("too many ISO9660 entries")
    names, validated = set(), []
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("invalid ISO entry")
        name = item.get("name")
        if (not isinstance(name, str) or not name or "\\" in name
                or name.startswith("/") or any(p in ("", ".", "..") for p in name.split("/"))):
            raise ValueError("invalid ISO entry name")
        if name.upper() in names:
            raise ValueError("duplicate ISO filename")
        names.add(name.upper())
        lba = _nonnegative(item.get("lba"), "file LBA")
        size = _nonnegative(item.get("bytes"), "file byte size", MAX_ISO_FILE_BYTES)
        sectors = (size + USER_SECTOR_BYTES - 1) // USER_SECTOR_BYTES
        if lba + sectors > MAX_LBA:
            raise ValueError("ISO extent exceeds bounded sector range")
        validated.append((name.upper(), lba, lba + sectors))
    return validated


def _merge(intervals):
    result = []
    for left, right in sorted(intervals):
        if not result or left > result[-1][1]:
            result.append([left, right])
        else:
            result[-1][1] = max(result[-1][1], right)
    return result


def _interval_size(intervals):
    return sum(right - left for left, right in intervals)


def _overlap_with_file(intervals, start, end):
    if end == start:
        return []
    return _merge(
        [(max(start, left), min(end, right))
         for left, right in intervals
         if min(end, right) > max(start, left)]
    )


def _subtract_size(primary, controls):
    """Count union(primary) minus union(controls), not duplicate read calls."""
    total = 0
    for left, right in primary:
        at = left
        for control_left, control_right in controls:
            if control_right <= at:
                continue
            if control_left >= right:
                break
            total += max(0, min(right, control_left) - at)
            at = min(right, max(at, control_right))
            if at >= right:
                break
        total += right - at
    return total


def _validate_trace(trace):
    if not isinstance(trace, dict) or trace.get("schema_version") != 1 or isinstance(trace.get("schema_version"), bool):
        raise ValueError("invalid trace schema")
    if trace.get("addressing") != ADDRESSING:
        raise ValueError("read trace must use ISO9660 logical data-sector LBA")
    runs = trace.get("runs")
    if not isinstance(runs, list) or not 2 <= len(runs) <= MAX_RUNS:
        raise ValueError("need bounded menu-control and battle-entry runs")
    seen = set()
    validated = []
    for run in runs:
        if not isinstance(run, dict) or run.get("phase") not in PHASES:
            raise ValueError("unknown trace phase")
        phase = run["phase"]
        seen.add(phase)
        events = run.get("reads")
        if not isinstance(events, list) or not 1 <= len(events) <= MAX_EVENTS_PER_RUN:
            raise ValueError("each capture run needs sector-read observations")
        extents = []
        for event in events:
            if not isinstance(event, dict):
                raise ValueError("invalid read event")
            lba = _nonnegative(event.get("lba"), "trace LBA")
            count = _nonnegative(event.get("sectors"), "trace sector count")
            if not 1 <= count <= MAX_LBA or lba + count > MAX_LBA:
                raise ValueError("out-of-range trace read extent")
            extents.append((lba, lba + count))
        validated.append((phase, _merge(extents)))
    if seen != PHASES:
        raise ValueError("both first-battle and menu-control runs required")
    return validated


def crosswalk(inventory, trace):
    """Analyze only allowlisted candidate names; never emit arbitrary source fields."""
    files = _validate_inventory(inventory)
    runs = _validate_trace(trace)
    by_name = {name: (start, end) for name, start, end in files}
    battle_runs = [read for phase, read in runs if phase == "first_battle_entry"]
    menu_runs = [read for phase, read in runs if phase == "menu_control"]

    candidates = []
    for name in CANDIDATES:
        extent = by_name.get(name)
        if extent is None:
            candidates.append({
                "candidate_name": name, "present_in_iso": False,
                "first_battle_runs_with_reads": 0, "menu_runs_with_reads": 0,
                "battle_sectors": 0, "menu_sectors": 0,
                "battle_exclusive_sectors": 0, "ambiguous_iso_extent": False,
                "observation": "candidate_absent",
                "loader_relationship_verified": False,
            })
            continue
        start, end = extent
        collisions = any(
            other_name != name and other_end > start and other_start < end
            for other_name, other_start, other_end in files
        )
        battle_spans = _merge([
            interval
            for read in battle_runs
            for interval in _overlap_with_file(read, start, end)
        ])
        control_spans = _merge([
            interval
            for read in menu_runs
            for interval in _overlap_with_file(read, start, end)
        ])
        battle_count = sum(bool(_overlap_with_file(r, start, end)) for r in battle_runs)
        menu_count = sum(bool(_overlap_with_file(r, start, end)) for r in menu_runs)
        observation = (
            "ambiguous_extent" if collisions else
            "observed_in_battle_and_control" if battle_count and menu_count else
            "observed_in_battle_only" if battle_count else
            "observed_in_control_only" if menu_count else
            "not_observed"
        )
        candidates.append({
            "candidate_name": name, "present_in_iso": True,
            "first_battle_runs_with_reads": battle_count,
            "menu_runs_with_reads": menu_count,
            "battle_sectors": _interval_size(battle_spans),
            "menu_sectors": _interval_size(control_spans),
            "battle_exclusive_sectors": _subtract_size(battle_spans, control_spans),
            "ambiguous_iso_extent": collisions,
            "observation": observation,
            "loader_relationship_verified": False,
        })
    return {
        "schema_version": 1,
        "kind": "SATURN_SECTOR_READ_HYPOTHESIS_ONLY",
        "addressing": ADDRESSING,
        "run_counts": {
            "first_battle_entry": len(battle_runs),
            "menu_control": len(menu_runs),
        },
        "candidate_results": candidates,
        "trace_origin_authenticated": False,
        "first_battle_map_identified": False,
        "japanese_master_equivalence_verified": False,
        "limitations": [
            "Read overlap is not executable load provenance or proof of file purpose.",
            "An incomplete menu trace cannot prove battle-specific reads.",
            "ISO logical LBA is not raw physical MSF or an implicitly shifted +150 address.",
            "Overlapping ISO file extents make attribution ambiguous.",
            "No original Saturn media or observed first-battle trace is bundled.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True,
                        help="Private ISO9660 metadata JSON from saturn_iso --list-files")
    parser.add_argument("--trace", type=Path, required=True,
                        help="Locally captured ISO-relative sector read observations")
    parser.add_argument("--output", type=Path, help="Metadata-only result JSON path")
    args = parser.parse_args()
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        trace = json.loads(args.trace.read_text(encoding="utf-8"))
        result = crosswalk(inventory, trace)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
        # Do not echo private paths, disc details or raw logs into CI output.
        print("SATURN_READ_CROSSWALK_REJECTED " + type(exc).__name__, file=sys.stderr)
        return 1
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
