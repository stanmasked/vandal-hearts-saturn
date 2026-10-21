#!/usr/bin/env python3
"""Stage76: numeric-only Yabause callback logs to Stage73-75 logical-LBA traces.

Each file is ONE privately recorded Yabause session. The caller must verify
which original gameplay state and release edition the capture represents.
The tool does not read a disc, screen frame, save file or sector payload.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from tools.saturn_fad_trace import convert_fad_trace, FAD_ADDRESSING
from tools.saturn_read_crosswalk import MAX_EVENTS_PER_RUN, MAX_RUNS

LINE = re.compile(r"VHCD_FAD (0|[1-9][0-9]{0,8})\Z")
MAX_LOG_BYTES = 400_000


def parse_fad_log(raw: str) -> list[dict]:
    if not isinstance(raw, str) or not raw or len(raw.encode("utf-8")) > MAX_LOG_BYTES:
        raise ValueError("invalid or oversized numeric log")
    lines = raw.splitlines()
    if not 1 <= len(lines) <= MAX_EVENTS_PER_RUN:
        raise ValueError("too many or too few CD read events")
    result = []
    for line in lines:
        match = LINE.fullmatch(line)
        if match is None:
            raise ValueError("unrecognized Yabause CD event")
        result.append({"fad": int(match.group(1)), "sectors": 1})
    return result


def build_private_trace(track1_sectors, phase_logs: list[tuple[str, str]]) -> dict:
    if not isinstance(phase_logs, list) or not 4 <= len(phase_logs) <= MAX_RUNS:
        raise ValueError("at least two battle and two menu runs required")
    runs = []
    for phase, content in phase_logs:
        if phase not in ("first_battle_entry", "menu_control"):
            raise ValueError("unknown capture phase")
        runs.append({"phase": phase, "reads": parse_fad_log(content)})
    if (sum(x["phase"] == "first_battle_entry" for x in runs) < 2 or
            sum(x["phase"] == "menu_control" for x in runs) < 2):
        raise ValueError("need at least two logs per phase")
    return convert_fad_trace(
        {"schema_version": 1, "addressing": FAD_ADDRESSING, "runs": runs},
        track1_sectors
    )


def _read_local(path: Path) -> str:
    if path.stat().st_size > MAX_LOG_BYTES:
        raise ValueError("oversized private log")
    return path.read_text(encoding="ascii")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inventory", required=True, type=Path)
    p.add_argument("--battle-log", required=True, action="append", type=Path)
    p.add_argument("--menu-log", required=True, action="append", type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    try:
        sources = ([("first_battle_entry", f) for f in args.battle_log] +
                   [("menu_control", f) for f in args.menu_log])
        resolved = [f.resolve() for _, f in sources]
        if (len(resolved) != len(set(resolved)) or
                args.output.resolve() in resolved or
                args.inventory.resolve() in resolved or
                args.output.resolve() == args.inventory.resolve()):
            raise ValueError("duplicate log or clashing output")
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        data = [(phase, _read_local(path)) for phase, path in sources]
        normalized = build_private_trace(inventory["sectors"], data)
        if args.output.exists():
            raise ValueError("refuse overwrite of existing private output")
        args.output.write_text(json.dumps(normalized, indent=2) + "\n",
                               encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError,
            TypeError, KeyError) as exc:
        print("YABAUSE_FAD_LOG_REJECTED " + type(exc).__name__, file=sys.stderr)
        return 1
    print("YABAUSE_FAD_LOG_NORMALIZED runs=" + str(len(normalized["runs"])) +
          " source_authenticated=false capture_independence_verified=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
