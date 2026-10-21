#!/usr/bin/env python3
"""Stage67: evidence-coverage gate for an *observed*, not authenticated, Saturn battle.

Never reads original media; emits aggregated counts and blocker codes only.
A complete manifest is not proof that it came from the genuine Japanese disc,
that its battle rules are correct, or that the native port can play it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.saturn_battle_evidence import validate_document

REQUIRED_OBSERVATIONS = frozenset({"movement", "attack", "turn_order"})
MAX_NATIVE_DIM = 128


def assess_coverage(document):
    """Return only safe aggregate counts and deterministic blocker codes."""
    validation = validate_document(document)
    if not validation["valid"]:
        return {
            "schema_valid": False, "coverage_complete": False,
            "counts": {}, "blockers": ["INVALID_EVIDENCE_MANIFEST"],
            "authenticity_verified": False,
            "native_battle_verified": False,
        }

    source = document["source"]
    scene = document["scene"]
    cells = document["cells"]
    units = document["units"]
    turns = document["turns"]
    observations = document["observations"]
    width, height = scene["width"], scene["height"]
    expected = width * height
    evidence_ids = {e["id"] for e in document["evidence"]}
    blockers = set()

    if width > MAX_NATIVE_DIM or height > MAX_NATIVE_DIM:
        blockers.add("DIMENSIONS_EXCEED_NATIVE_BATTLE")
    if scene["status"] != "observed":
        blockers.add("SCENE_GRID_NOT_OBSERVED")
    if len(cells) != expected:
        blockers.add("GRID_COVERAGE_INCOMPLETE")
    if not cells:
        blockers.add("GRID_COVERAGE_INCOMPLETE")

    missing_cells = 0
    for cell in cells:
        complete = (
            cell["confidence"] == "observed"
            and bool(cell.get("evidence_ids"))
            and all(ref in evidence_ids for ref in cell.get("evidence_ids", []))
            and cell.get("terrain") is not None
            and cell.get("elevation") is not None
            and cell.get("traversable") is not None
            and cell.get("movement_cost") is not None
        )
        if not complete:
            missing_cells += 1
    if missing_cells:
        blockers.add("CELLS_REQUIRE_OBSERVED_VALUES_AND_EVIDENCE")

    players = sum(u["team"] == "player" for u in units)
    enemies = sum(u["team"] == "enemy" for u in units)
    if not players or not enemies:
        blockers.add("ROSTER_REQUIRES_BOTH_SIDES")

    incomplete_units = 0
    positions = set()
    for unit in units:
        pos = (unit["x"], unit["y"])
        if pos in positions:
            blockers.add("UNIT_POSITIONS_OVERLAP")
        positions.add(pos)
        matching_cell = next(
            (cell for cell in cells if cell["x"] == pos[0] and cell["y"] == pos[1]),
            None,
        )
        if matching_cell is None or matching_cell.get("traversable") is not True:
            blockers.add("UNIT_NOT_ON_CONFIRMED_WALKABLE_CELL")
        if not (unit["confidence"] == "observed" and unit.get("evidence_ids")
                and unit.get("hp") is not None and unit["hp"] > 0
                and unit.get("max_hp") is not None
                and unit.get("move_points") is not None):
            incomplete_units += 1
    if incomplete_units:
        blockers.add("UNITS_REQUIRE_OBSERVED_STATS_AND_EVIDENCE")

    observed_kinds = {
        o["kind"] for o in observations
        if o["confidence"] == "observed" and o.get("evidence_ids")
    }
    missing_kinds = sorted(REQUIRED_OBSERVATIONS - observed_kinds)
    if missing_kinds:
        blockers.add("REQUIRED_MECHANICS_NOT_OBSERVED")

    if not ({"victory", "defeat"} & observed_kinds):
        blockers.add("TERMINAL_OUTCOME_NOT_OBSERVED")

    unit_sides = {unit["id"]: unit["team"] for unit in units}
    action_count = 0
    unsupported_actions = 0
    recorded_action_kinds = set()
    prior_round = 0
    for turn in turns:
        # A full battle replay requires round numbers in monotone order.
        if turn["round"] < prior_round:
            blockers.add("ROUND_ORDER_INCONSISTENT")
        prior_round = turn["round"]
        for action in turn.get("actions", []):
            action_count += 1
            recorded_action_kinds.add(action["kind"])
            actor = action.get("actor_id")
            target = action.get("target_id")
            if not actor or not action.get("evidence_ids"):
                unsupported_actions += 1
            if actor is not None and unit_sides.get(actor) != turn["active_side"]:
                blockers.add("ACTION_ACTOR_SIDE_MISMATCH")
            if action["kind"] == "attack" and (target is None or target == actor):
                blockers.add("ATTACK_TARGET_NOT_IDENTIFIED")
    if not turns or not action_count or unsupported_actions:
        blockers.add("ACTION_TRACE_INCOMPLETE")
    if not {"move", "attack"} <= recorded_action_kinds:
        blockers.add("BATTLE_ACTION_TYPES_INCOMPLETE")

    # A filled form is not an authenticated release or a replicated battle.
    return {
        "schema_valid": True,
        "coverage_complete": not blockers,
        "counts": {
            "expected_cells": expected,
            "recorded_cells": len(cells),
            "cells_missing_evidence_or_values": missing_cells,
            "units": len(units),
            "units_missing_evidence_or_stats": incomplete_units,
            "player_units": players,
            "enemy_units": enemies,
            "mechanic_types_observed": len(observed_kinds & REQUIRED_OBSERVATIONS),
            "mechanic_types_required": len(REQUIRED_OBSERVATIONS),
            "terminal_observation_count": sum(
                o["kind"] in {"victory", "defeat"} and o["confidence"] == "observed"
                and bool(o.get("evidence_ids")) for o in observations),
            "turns": len(turns),
            "actions": action_count,
            "actions_missing_actor_or_evidence": unsupported_actions,
        },
        "blockers": sorted(blockers),
        "authenticity_verified": False,
        "native_battle_verified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, help="Private or locally approved summary path")
    args = parser.parse_args()
    try:
        document = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = assess_coverage(document)
    except (OSError, UnicodeError, json.JSONDecodeError):
        result = {"schema_valid": False, "coverage_complete": False,
                  "counts": {}, "blockers": ["UNREADABLE_JSON"],
                  "authenticity_verified": False, "native_battle_verified": False}
    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0 if result["coverage_complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
