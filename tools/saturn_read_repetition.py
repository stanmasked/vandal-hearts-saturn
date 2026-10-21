#!/usr/bin/env python3
"""Stage74: repeatability gate for metadata-only first-battle read hypotheses.

Require repeated presence of the exact same candidate ISO sectors across
multiple submitted battle-entry runs and compare against the UNION of menu
control observations. This is not proof that runs are truly independent,
controls complete, that a resource was parsed, or of Saturn authenticity.
No original disc contents, screenshots, or private paths are read/exported.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.saturn_read_crosswalk import (
    CANDIDATES, _interval_size, _merge, _overlap_with_file,
    _subtract_size, _validate_inventory, _validate_trace,
)

MAX_REQUIRED_RUNS = 8


def _intersect_sorted(left, right):
    """Intersect two merged, non-overlapping interval lists (half-open)."""
    i = j = 0
    shared = []
    while i < len(left) and j < len(right):
        a, b = left[i]
        c, d = right[j]
        lo, hi = max(a, c), min(b, d)
        if lo < hi:
            shared.append((lo, hi))
        if b < d:
            i += 1
        elif d < b:
            j += 1
        else:
            i += 1
            j += 1
    return _merge(shared)


def _common_sectors(clipped_per_run):
    if not clipped_per_run:
        return []
    overlap = clipped_per_run[0]
    for candidate in clipped_per_run[1:]:
        overlap = _intersect_sorted(overlap, candidate)
        if not overlap:
            break
    return overlap


def analyze_repeatability(inventory, trace, *, min_battle=2, min_control=2):
    if (type(min_battle) is not int or type(min_control) is not int
            or not 2 <= min_battle <= MAX_REQUIRED_RUNS
            or not 2 <= min_control <= MAX_REQUIRED_RUNS):
        raise ValueError("repeatability gate requires 2..8 runs per phase")
    files = _validate_inventory(inventory)
    runs = _validate_trace(trace)
    battles = [intervals for phase, intervals in runs if phase == "first_battle_entry"]
    controls = [intervals for phase, intervals in runs if phase == "menu_control"]
    enough = len(battles) >= min_battle and len(controls) >= min_control
    by_name = {name: (start, end) for name, start, end in files}
    results = []

    for name in CANDIDATES:
        if name not in by_name:
            results.append({
                "candidate_name": name, "status": "candidate_absent",
                "battle_runs_with_candidate": 0, "menu_runs_with_candidate": 0,
                "common_battle_sectors": 0, "common_battle_not_in_any_menu": 0,
                "overlapping_iso_extents": False,
                "runtime_loader_verified": False,
            })
            continue
        start, end = by_name[name]
        ambiguous = any(
            other_name != name and start < other_end and other_start < end
            for other_name, other_start, other_end in files
        )
        b = [_overlap_with_file(read, start, end) for read in battles]
        c = [_overlap_with_file(read, start, end) for read in controls]
        common = _common_sectors(b)
        controls_union = _merge([span for run in c for span in run])
        repeated = _interval_size(common)
        differential = _subtract_size(common, controls_union)
        if not enough:
            status = "insufficient_repeated_capture_runs"
        elif ambiguous:
            status = "ambiguous_iso_extent"
        elif repeated == 0:
            status = "no_sector_common_to_all_battle_runs"
        elif differential == 0:
            status = "all_repeated_sectors_seen_in_menu_controls"
        else:
            status = "repeated_battle_differential_candidate_only"
        results.append({
            "candidate_name": name,
            "status": status,
            "battle_runs_with_candidate": sum(bool(x) for x in b),
            "menu_runs_with_candidate": sum(bool(x) for x in c),
            "common_battle_sectors": repeated,
            "common_battle_not_in_any_menu": differential,
            "overlapping_iso_extents": ambiguous,
            "runtime_loader_verified": False,
        })

    return {
        "schema_version": 1,
        "kind": "SATURN_SECTOR_REPETITION_UNVERIFIED",
        "runs_submitted": {"first_battle_entry": len(battles),
                           "menu_control": len(controls)},
        "minimum_runs_required": {
            "first_battle_entry": min_battle, "menu_control": min_control,
        },
        "numeric_repetition_gate_ready": enough,
        "results": results,
        "capture_independence_verified": False,
        "control_window_completeness_verified": False,
        "source_media_authenticated": False,
        "first_battle_map_identified": False,
        "combat_rules_verified": False,
        "limitations": [
            "Submitted repeated runs could be duplicated; independent capture provenance is not verified.",
            "Even repeated battle-exclusive sector reads do not prove resource purpose or loader use.",
            "Missing menu reads are not evidence of exclusivity when control windows are incomplete.",
            "Sector-address calibration and source edition must be independently corroborated.",
            "No authentic Saturn read traces or game payloads are included in public CI.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True,
                        help="Private, calibrated Stage73 logical-sector trace")
    parser.add_argument("--output", type=Path, help="Private aggregate report JSON")
    args = parser.parse_args()
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        trace = json.loads(args.trace.read_text(encoding="utf-8"))
        result = analyze_repeatability(inventory, trace)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError,
            TypeError, KeyError) as exc:
        print("SATURN_READ_REPETITION_REJECTED " + type(exc).__name__, file=sys.stderr)
        return 1
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0 if result["numeric_repetition_gate_ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
