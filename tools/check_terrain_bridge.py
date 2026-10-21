#!/usr/bin/env python3
"""Stage69: synthetic-only Python terrain export -> real compiled C++ parser.

Builds an invented 2x2 Stage66 manifest, checks Stage67 completeness and
Stage68 serialization, and invokes the actual native parser. This program
must never be fed the private Saturn dump in public CI.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile
from tools.saturn_terrain_bridge import export_numeric_terrain

PROBE = re.compile(
    r"VH_TERRAIN_PROBE size=(\d+)x(\d+) cells=(\d+) "
    r"walkable=(\d+) blocked=(\d+) cost_sum=(-?\d+) "
    r"elevation_sum=(-?\d+) units=(\d+)"
)


def synthetic_manifest():
    cells = [
        {"x": x, "y": y, "terrain": "invented floor", "elevation": 0,
         "movement_cost": 1, "traversable": True, "confidence": "observed",
         "evidence_ids": ["local-fixture"]}
        for y in range(2) for x in range(2)
    ]
    cells[1]["elevation"] = 1
    cells[1]["movement_cost"] = 2
    cells[2]["traversable"] = False
    return {
        "schema_version": 1,
        "source": {"platform": "Sega Saturn", "product_code": "T-9526G",
                   "release_label": "FAKE TEST ONLY", "capture_kind": "emulator"},
        "scene": {"label": "FAKE INDEPENDENT GRID", "width": 2, "height": 2,
                  "coordinate_system": "x-right-y-down", "status": "observed"},
        "evidence": [{"id": "local-fixture", "kind": "manual_note",
                      "artifact_ref": "private-ref:fake-test-fixture"}],
        "cells": cells,
        "units": [
            {"id": "ally", "team": "player", "class_label": None,
             "x": 0, "y": 0, "hp": 10, "max_hp": 10,
             "move_points": 2, "confidence": "observed",
             "evidence_ids": ["local-fixture"]},
            {"id": "enemy", "team": "enemy", "class_label": None,
             "x": 1, "y": 1, "hp": 10, "max_hp": 10,
             "move_points": 2, "confidence": "observed",
             "evidence_ids": ["local-fixture"]},
        ],
        "observations": [
            {"id": name, "kind": name, "claim": "invented synthetic test",
             "confidence": "observed", "evidence_ids": ["local-fixture"]}
            for name in ("movement", "attack", "turn_order", "victory")
        ],
        "turns": [{"round": 1, "active_side": "player",
                   "actions": [
                       {"kind": "move", "actor_id": "ally",
                        "to": {"x": 1, "y": 0}, "evidence_ids": ["local-fixture"]},
                       {"kind": "attack", "actor_id": "ally", "target_id": "enemy",
                        "evidence_ids": ["local-fixture"]},
                   ]}],
    }


def parse_receipt(text):
    match = PROBE.fullmatch(text.strip())
    if not match:
        raise ValueError("unexpected C++ terrain probe receipt")
    nums = tuple(int(v) for v in match.groups())
    if nums[2] != nums[3] + nums[4] or nums[7] != 0:
        raise ValueError("impossible native terrain grid or unexpected units")
    return nums


def verify(binary: Path):
    if not binary.is_file():
        raise FileNotFoundError("compiled terrain probe missing")
    document = synthetic_manifest()
    serialized = export_numeric_terrain(document)
    if "FAKE" in serialized or "private-ref" in serialized:
        raise AssertionError("export leaked synthetic source metadata")
    with tempfile.TemporaryDirectory(prefix="vh-terrain-synthetic-") as temp:
        path = Path(temp) / "synthetic.vhterrain"

        def run(text, expect_valid):
            path.write_text(text, encoding="ascii")
            process = subprocess.run([str(binary.resolve()), str(path)],
                                     capture_output=True, text=True, timeout=15)
            if expect_valid:
                if process.returncode != 0 or process.stderr:
                    raise AssertionError("native parser rejected valid synthetic grid")
                return parse_receipt(process.stdout)
            if (process.returncode == 0 or process.stdout.strip()
                    or process.stderr.strip() != "TERRAIN_PROBE_REJECTED"):
                raise AssertionError("native parser did not reject malformed grid")
            return None

        baseline = run(serialized, True)
        expected = (2, 2, 4, 3, 1, 5, 1, 0)
        if baseline != expected:
            raise AssertionError("Python export and C++ terrain interpretation diverged")

        # A valid but changed numeric value must change the native aggregate.
        raised = serialized.replace("CELL 1 0 1 2 1", "CELL 1 0 1 3 1")
        if raised == serialized:
            raise AssertionError("synthetic cost mutation not applied")
        changed = run(raised, True)
        if changed != (2, 2, 4, 3, 1, 6, 1, 0):
            raise AssertionError("native parser ignored one changed movement cost")

        tests = {
            "missing_cell": serialized.rsplit("CELL ", 1)[0],
            "extra_cell": serialized + "CELL 0 0 0 1 1\n",
            "reordered": serialized.replace("CELL 0 0 0 1 1", "CELL 1 0 0 1 1"),
            "bad_cost": serialized.replace("CELL 1 0 1 2 1", "CELL 1 0 1 0 1"),
            "bad_passable": serialized.replace("CELL 0 1 0 1 0", "CELL 0 1 0 1 2"),
            "overflow": serialized.replace("CELL 1 0 1 2 1",
                                           "CELL 1 0 9999999999999999999 2 1"),
            "bad_header": serialized.replace("VH_TERRAIN_UNVERIFIED_V1",
                                              "VH_TERRAIN_AUTHENTIC_V1"),
        }
        for name, changed_text in tests.items():
            if changed_text == serialized:
                raise AssertionError("failed to apply mutation: " + name)
            run(changed_text, False)

        return {
            "fixture": "invented_2x2_no_original_media",
            "schema_gate": True,
            "python_export_to_cpp": True,
            "numeric_cost_change_detected": True,
            "adversarial_rejections": len(tests),
            "native_units_created": False,
            "Saturn_source_verified": False,
            "real_battle_playable": False,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = verify(args.binary)
    result = json.dumps(receipt, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    print(result, end="")


if __name__ == "__main__":
    main()
