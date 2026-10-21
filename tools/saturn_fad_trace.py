#!/usr/bin/env python3
"""Stage73: explicit Saturn CD-block FAD -> ISO9660 Track-1 logical-LBA conversion.

The documented Saturn hardware addressing is FAD = LBA + 150 for the first
data track. Only convert explicitly labeled FAD logs with a known Track-1
sector count; never infer this offset from match quality.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.saturn_read_crosswalk import (
    ADDRESSING, MAX_LBA, PHASES, _validate_trace,
)

FAD_ADDRESSING = "saturn_cd_block_fad"
FAD_LEAD_IN = 150


def convert_fad_trace(trace, track1_sectors):
    if (type(track1_sectors) is not int or
            not 17 <= track1_sectors <= MAX_LBA - FAD_LEAD_IN):
        raise ValueError("invalid Track-1 sector count")
    if (not isinstance(trace, dict) or
            type(trace.get("schema_version")) is not int or
            trace["schema_version"] != 1 or
            trace.get("addressing") != FAD_ADDRESSING):
        raise ValueError("expected explicitly labeled Saturn CD-block FAD trace")
    original_runs = trace.get("runs")
    if not isinstance(original_runs, list):
        raise ValueError("missing FAD runs")

    runs = []
    for source_run in original_runs:
        if (not isinstance(source_run, dict) or
                not isinstance(source_run.get("phase"), str) or
                source_run["phase"] not in PHASES or
                not isinstance(source_run.get("reads"), list)):
            raise ValueError("invalid FAD run")
        converted_reads = []
        for read in source_run["reads"]:
            if not isinstance(read, dict):
                raise ValueError("invalid FAD event")
            fad, count = read.get("fad"), read.get("sectors")
            if (type(fad) is not int or type(count) is not int or
                    count < 1 or fad < FAD_LEAD_IN or
                    fad + count > FAD_LEAD_IN + track1_sectors):
                raise ValueError("FAD range outside known Track 1")
            converted_reads.append({"lba": fad - FAD_LEAD_IN,
                                    "sectors": count})
        runs.append({"phase": source_run["phase"], "reads": converted_reads})
    converted = {"schema_version": 1, "addressing": ADDRESSING, "runs": runs}
    # Reuse Stage73 bounds, phases, nonempty-control and interval validation.
    _validate_trace(converted)
    return converted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path,
                        help="Private SaturnISO metadata with sectors count")
    parser.add_argument("--fad-trace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path,
                        help="Local/private normalized logical LBA trace")
    args = parser.parse_args()
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        trace = json.loads(args.fad_trace.read_text(encoding="utf-8"))
        converted = convert_fad_trace(trace, inventory["sectors"])
        args.output.write_text(json.dumps(converted, indent=2) + "\n", encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError,
            ValueError, KeyError) as exc:
        # Paths, run-local labels and media never appear in error diagnostics.
        print("SATURN_FAD_TRACE_REJECTED " + type(exc).__name__, file=sys.stderr)
        return 1
    print("SATURN_FAD_TO_LBA_CONVERTED hypothetical_trace=true "
          "source_authenticated=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
