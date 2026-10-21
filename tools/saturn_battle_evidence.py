#!/usr/bin/env python3
"""Validate a private, evidence-linked Saturn battle observation manifest.

The validator handles only user-authored structured observations. It never
opens screenshots/video or reads the disc. Its summary omits claims, artifact
references, asset bytes, paths and source hashes.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

CONFIDENCE = {"observed", "inferred", "uncertain", "unknown"}
EVIDENCE_KINDS = {"screenshot", "video_frame", "emulator_log",
                  "control_trace", "manual_note"}
CAPTURE_KINDS = {"emulator", "physical_saturn", "video_recording", "manual"}
OBSERVATION_KINDS = {"position", "movement", "attack", "damage", "turn_order",
                      "victory", "defeat", "terrain", "other"}
ACTION_KINDS = {"move", "attack", "defend", "cast", "end_turn", "use_item", "unknown"}
SIDES = {"player", "enemy", "neutral", "unknown"}
PRIVATE_REF = re.compile(r"private-ref:[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _object(value, path, errors):
    if not isinstance(value, dict):
        errors.append(path + ": expected object")
        return {}
    return value


def _array(value, path, errors):
    if not isinstance(value, list):
        errors.append(path + ": expected array")
        return []
    return value


def _string(value, path, errors, *, optional=False):
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(path + ": expected non-empty string")
        return None
    return value


def _integer(value, path, errors, *, minimum=0, optional=False):
    if optional and value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        errors.append(path + f": expected integer >= {minimum}")
        return None
    return value


def _enum(value, choices, path, errors):
    if not isinstance(value, str) or value not in choices:
        errors.append(path + ": unsupported value")
        return None
    return value


def _coord(value, path, width, height, errors, *, optional=True):
    if value is None and optional:
        return None
    point = _object(value, path, errors)
    x = _integer(point.get("x"), path + ".x", errors)
    y = _integer(point.get("y"), path + ".y", errors)
    if x is None or y is None:
        return None
    if width is not None and height is not None and (x >= width or y >= height):
        errors.append(path + ": coordinate outside scene bounds")
        return None
    return (x, y)


def _evidence_refs(value, path, evidence_ids, errors):
    refs = _array(value if value is not None else [], path, errors)
    for i, ref in enumerate(refs):
        if not isinstance(ref, str) or ref not in evidence_ids:
            errors.append(f"{path}[{i}]: unknown evidence id")
    return refs


def validate_document(document):
    errors, warnings = [], []
    if not isinstance(document, dict):
        return {"valid": False, "errors": ["$: expected object"], "warnings": [],
                "summary": {}}

    version = document.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version != 1:
        errors.append("$.schema_version: expected integer 1")
    source = _object(document.get("source"), "$.source", errors)
    platform = _string(source.get("platform"), "$.source.platform", errors)
    if platform is not None and platform != "Sega Saturn":
        errors.append("$.source.platform: expected Sega Saturn")
    product_code = _string(source.get("product_code"), "$.source.product_code", errors)
    release_label = _string(source.get("release_label"), "$.source.release_label", errors)
    capture_kind = _enum(source.get("capture_kind"), CAPTURE_KINDS,
                         "$.source.capture_kind", errors)

    scene = _object(document.get("scene"), "$.scene", errors)
    label = _string(scene.get("label"), "$.scene.label", errors)
    width = _integer(scene.get("width"), "$.scene.width", errors, minimum=1)
    height = _integer(scene.get("height"), "$.scene.height", errors, minimum=1)
    if width is not None and width > 512:
        errors.append("$.scene.width: exceeds supported limit 512")
        width = None
    if height is not None and height > 512:
        errors.append("$.scene.height: exceeds supported limit 512")
        height = None
    if scene.get("coordinate_system") != "x-right-y-down":
        errors.append("$.scene.coordinate_system: expected x-right-y-down")
    scene_status = _enum(scene.get("status"), {"unknown", "partial", "observed"},
                         "$.scene.status", errors)

    evidence = _array(document.get("evidence"), "$.evidence", errors)
    evidence_ids = set()
    for i, raw in enumerate(evidence):
        path = f"$.evidence[{i}]"
        item = _object(raw, path, errors)
        ident = _string(item.get("id"), path + ".id", errors)
        if ident:
            if ident in evidence_ids:
                errors.append(path + ".id: duplicate evidence id")
            evidence_ids.add(ident)
        _enum(item.get("kind"), EVIDENCE_KINDS, path + ".kind", errors)
        ref = _string(item.get("artifact_ref"), path + ".artifact_ref", errors)
        if ref and not PRIVATE_REF.fullmatch(ref):
            errors.append(path + ".artifact_ref: use opaque private-ref:ID, not a path or URL")
        if item.get("note") is not None and not isinstance(item.get("note"), str):
            errors.append(path + ".note: expected string")

    cells = _array(document.get("cells"), "$.cells", errors)
    cell_positions = set()
    unknown_terrain = unknown_elevation = unknown_cost = 0
    for i, raw in enumerate(cells):
        path = f"$.cells[{i}]"
        cell = _object(raw, path, errors)
        x = _integer(cell.get("x"), path + ".x", errors)
        y = _integer(cell.get("y"), path + ".y", errors)
        if x is not None and y is not None:
            if width is not None and height is not None and (x >= width or y >= height):
                errors.append(path + ": coordinate outside scene bounds")
            if (x, y) in cell_positions:
                errors.append(path + ": duplicate cell coordinate")
            cell_positions.add((x, y))
        terrain = cell.get("terrain")
        if terrain is not None and (not isinstance(terrain, str) or not terrain.strip()):
            errors.append(path + ".terrain: expected non-empty string or null")
        if terrain is None:
            unknown_terrain += 1
        elevation = _integer(cell.get("elevation"), path + ".elevation", errors,
                             optional=True)
        movement_cost = _integer(cell.get("movement_cost"), path + ".movement_cost",
                                 errors, minimum=1, optional=True)
        if elevation is None:
            unknown_elevation += 1
        if movement_cost is None:
            unknown_cost += 1
        if cell.get("traversable") is not None and not isinstance(cell.get("traversable"), bool):
            errors.append(path + ".traversable: expected boolean or null")
        _enum(cell.get("confidence"), CONFIDENCE, path + ".confidence", errors)
        _evidence_refs(cell.get("evidence_ids", []), path + ".evidence_ids",
                       evidence_ids, errors)

    units = _array(document.get("units"), "$.units", errors)
    unit_ids, occupied = set(), {}
    unknown_hp = unknown_move = 0
    for i, raw in enumerate(units):
        path = f"$.units[{i}]"
        unit = _object(raw, path, errors)
        ident = _string(unit.get("id"), path + ".id", errors)
        if ident:
            if ident in unit_ids:
                errors.append(path + ".id: duplicate unit id")
            unit_ids.add(ident)
        _enum(unit.get("team"), SIDES - {"unknown"}, path + ".team", errors)
        class_label = unit.get("class_label")
        if class_label is not None and (not isinstance(class_label, str) or not class_label.strip()):
            errors.append(path + ".class_label: expected non-empty string or null")
        pos = _coord({"x": unit.get("x"), "y": unit.get("y")}, path,
                     width, height, errors, optional=False)
        if pos is not None:
            if pos in occupied:
                warnings.append(path + f": unit overlaps grid position also used by unit index {occupied[pos]}")
            else:
                occupied[pos] = i
        hp = _integer(unit.get("hp"), path + ".hp", errors, optional=True)
        max_hp = _integer(unit.get("max_hp"), path + ".max_hp", errors, optional=True)
        if hp is None:
            unknown_hp += 1
        if hp is not None and max_hp is not None and hp > max_hp:
            errors.append(path + ".hp: exceeds max_hp")
        if max_hp is not None and max_hp < 1:
            errors.append(path + ".max_hp: expected positive integer or null")
        move_points = _integer(unit.get("move_points"), path + ".move_points",
                               errors, optional=True)
        if move_points is None:
            unknown_move += 1
        _enum(unit.get("confidence"), CONFIDENCE, path + ".confidence", errors)
        _evidence_refs(unit.get("evidence_ids", []), path + ".evidence_ids",
                       evidence_ids, errors)

    observations = _array(document.get("observations"), "$.observations", errors)
    observation_ids = set()
    for i, raw in enumerate(observations):
        path = f"$.observations[{i}]"
        item = _object(raw, path, errors)
        ident = _string(item.get("id"), path + ".id", errors)
        if ident:
            if ident in observation_ids:
                errors.append(path + ".id: duplicate observation id")
            observation_ids.add(ident)
        _enum(item.get("kind"), OBSERVATION_KINDS, path + ".kind", errors)
        _string(item.get("claim"), path + ".claim", errors)
        _enum(item.get("confidence"), CONFIDENCE, path + ".confidence", errors)
        _evidence_refs(item.get("evidence_ids", []), path + ".evidence_ids",
                       evidence_ids, errors)

    turns = _array(document.get("turns"), "$.turns", errors)
    for i, raw in enumerate(turns):
        path = f"$.turns[{i}]"
        turn = _object(raw, path, errors)
        _integer(turn.get("round"), path + ".round", errors, minimum=1)
        _enum(turn.get("active_side"), SIDES, path + ".active_side", errors)
        actions = _array(turn.get("actions", []), path + ".actions", errors)
        for j, action_raw in enumerate(actions):
            ap = f"{path}.actions[{j}]"
            action = _object(action_raw, ap, errors)
            _enum(action.get("kind"), ACTION_KINDS, ap + ".kind", errors)
            for key in ("actor_id", "target_id"):
                ident = action.get(key)
                if ident is not None and (not isinstance(ident, str) or ident not in unit_ids):
                    errors.append(ap + f".{key}: unknown unit id")
            for key in ("from", "to"):
                if key in action:
                    _coord(action.get(key), ap + "." + key, width, height, errors)
            if action.get("result") is not None and not isinstance(action.get("result"), str):
                errors.append(ap + ".result: expected string or null")
            _evidence_refs(action.get("evidence_ids", []), ap + ".evidence_ids",
                           evidence_ids, errors)

    summary = {
        "source": {"platform": platform, "product_code": product_code,
                   "release_label": release_label, "capture_kind": capture_kind},
        "scene": {"label": label, "width": width, "height": height,
                  "status": scene_status},
        "counts": {"evidence": len(evidence), "cells": len(cells),
                   "units": len(units), "observations": len(observations),
                   "turns": len(turns)},
        "unknown_counts": {"cell_terrain": unknown_terrain,
                           "cell_elevation": unknown_elevation,
                           "cell_movement_cost": unknown_cost,
                           "unit_hp": unknown_hp, "unit_move_points": unknown_move},
        "overlap_warning_count": len(warnings),
    }
    return {"valid": not errors, "errors": errors, "warnings": warnings,
            "summary": summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Private user-authored JSON manifest")
    parser.add_argument("--summary", type=Path, help="Write validation summary only")
    args = parser.parse_args()
    try:
        document = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [type(exc).__name__],
                          "warnings": [], "summary": {}}, indent=2))
        return 2
    report = validate_document(document)
    output = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.summary:
        args.summary.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
