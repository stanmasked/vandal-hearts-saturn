#!/usr/bin/env python3
"""Stage75: privacy-safe preflight of self-declared Saturn capture provenance.

Requires explicit, one-to-one session metadata for Stage73/74 numeric read
traces. A reported PASS means only self-consistency + a match to the supplied
reference image fingerprint. It never proves independent recording, genuine
gameplay, loader identity, or original Japanese disc authenticity.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

from tools.saturn_read_crosswalk import _validate_trace
from tools.saturn_read_repetition import analyze_repeatability

IMAGE_SHA = re.compile(r"[0-9a-f]{64}\Z")
OPAQUE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
SOURCE_KIND = {"translation_patched", "unmodified", "unknown"}
INSTRUMENTATION = {"emulator_cd_block_hook", "hardware_cd_block_hook"}
BOOTS = {"cold_boot", "savestate"}
MAX_CAPTURE_FRAME = 10_000_000


def _opaque_id(value, what):
    if not isinstance(value, str) or not OPAQUE_ID.fullmatch(value):
        raise ValueError("invalid opaque " + what)
    return value


def _digest(value, what):
    if not isinstance(value, str) or not IMAGE_SHA.fullmatch(value):
        raise ValueError("invalid SHA-256 " + what)
    return value


def _enum(value, allowed, what):
    if not isinstance(value, str) or value not in allowed:
        raise ValueError("unsupported " + what)
    return value


def _frame(value, name):
    if type(value) is not int or not 0 <= value <= MAX_CAPTURE_FRAME:
        raise ValueError("invalid frame " + name)
    return value


def _duplicate_interval_pairs(runs, phase):
    """Equal numeric coverage can be normal for deterministic cold boots."""
    selected = [tuple(tuple(v) for v in spans)
                for name, spans in runs if name == phase]
    counts = Counter(selected)
    return sum(n * (n - 1) // 2 for n in counts.values())


def audit_capture_provenance(inventory, trace, sidecar, *,
                             expected_image_sha256=None):
    runs = _validate_trace(trace)
    numeric = analyze_repeatability(inventory, trace)
    if not isinstance(sidecar, dict) or type(sidecar.get("schema_version")) is not int or sidecar["schema_version"] != 1:
        raise ValueError("invalid capture sidecar schema")
    source = sidecar.get("source")
    if not isinstance(source, dict):
        raise ValueError("invalid capture source metadata")
    declared_hash = _digest(source.get("image_sha256"), "source image")
    _enum(source.get("release_kind"), SOURCE_KIND, "release kind")
    if source.get("product_code") != "T-9526G":
        raise ValueError("unexpected Saturn product code")
    _enum(sidecar.get("instrumentation"), INSTRUMENTATION,
          "instrumentation")
    declarations = sidecar.get("runs")
    if not isinstance(declarations, list) or len(declarations) != len(runs):
        raise ValueError("sidecar must match trace run count and order")
    if expected_image_sha256 is not None:
        expected_image_sha256 = _digest(expected_image_sha256, "reference image")

    capture_ids, session_ids = set(), set()
    mixed_images = 0
    mixed_releases = 0
    non_cold_boot = 0
    for index, (observation, (phase, _)) in enumerate(zip(declarations, runs)):
        if not isinstance(observation, dict):
            raise ValueError("malformed capture declaration")
        if observation.get("phase") != phase or not isinstance(observation.get("phase"), str):
            raise ValueError("sidecar phase does not match numeric trace")
        capture_id = _opaque_id(observation.get("capture_id"), "capture ID")
        session_id = _opaque_id(observation.get("session_id"), "session ID")
        if capture_id in capture_ids or session_id in session_ids:
            raise ValueError("reused capture or session identifier")
        capture_ids.add(capture_id)
        session_ids.add(session_id)
        image = _digest(observation.get("image_sha256"), "session image")
        kind = _enum(observation.get("release_kind"), SOURCE_KIND, "session release")
        boot = _enum(observation.get("boot_kind"), BOOTS, "boot kind")
        start = _frame(observation.get("frame_start"), "start")
        end = _frame(observation.get("frame_end"), "end")
        if end <= start:
            raise ValueError("nonpositive capture window")
        mixed_images += image != declared_hash
        mixed_releases += kind != source["release_kind"]
        non_cold_boot += boot != "cold_boot"

    blockers = []
    if not numeric["numeric_repetition_gate_ready"]:
        blockers.append("INSUFFICIENT_REPEATED_SECTOR_RUNS")
    if expected_image_sha256 is None:
        blockers.append("REFERENCE_IMAGE_FINGERPRINT_NOT_SUPPLIED")
    elif declared_hash != expected_image_sha256:
        blockers.append("REFERENCE_IMAGE_FINGERPRINT_MISMATCH")
    if mixed_images:
        blockers.append("INCONSISTENT_IMAGE_FINGERPRINTS")
    if mixed_releases:
        blockers.append("MIXED_RELEASE_KINDS")
    if non_cold_boot:
        blockers.append("SAVESTATE_RUN_NOT_COLD_BOOT")
    duplicates = {
        phase: _duplicate_interval_pairs(runs, phase)
        for phase in ("first_battle_entry", "menu_control")
    }

    return {
        "schema_version": 1,
        "kind": "SATURN_CAPTURE_METADATA_PREFLIGHT_ONLY",
        "metadata_preflight_ready_for_human_review": not blockers,
        "blockers": blockers,
        "counts": {
            "runs": len(runs),
            "first_battle_entry": numeric["runs_submitted"]["first_battle_entry"],
            "menu_control": numeric["runs_submitted"]["menu_control"],
            "distinct_declared_capture_ids": len(capture_ids),
            "distinct_declared_session_ids": len(session_ids),
            "non_cold_boot_runs": non_cold_boot,
            "mixed_image_fingerprint_runs": mixed_images,
            "mixed_release_kind_runs": mixed_releases,
            "identical_normalized_read_coverage_pairs": duplicates,
        },
        "source_consistency_self_reported_only": True,
        "identical_sector_reads_may_be_legitimate": True,
        "independent_capture_sessions_verified": False,
        "screen_state_synchronized_verified": False,
        "control_window_completeness_verified": False,
        "source_media_authenticated": False,
        "loader_relationship_verified": False,
        "first_battle_map_identified": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inventory", type=Path, required=True)
    p.add_argument("--trace", type=Path, required=True)
    p.add_argument("--capture-sidecar", type=Path, required=True)
    p.add_argument("--expected-image-sha256", required=False,
                   help="Locally pinned Track-1 SHA-256, no image data read")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        trace = json.loads(args.trace.read_text(encoding="utf-8"))
        sidecar = json.loads(args.capture_sidecar.read_text(encoding="utf-8"))
        report = audit_capture_provenance(
            inventory, trace, sidecar,
            expected_image_sha256=args.expected_image_sha256)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError,
            TypeError, KeyError) as error:
        # Do not echo private paths, hashes, capture IDs or source labels.
        print("SATURN_CAPTURE_PREFLIGHT_REJECTED " +
              type(error).__name__, file=sys.stderr)
        return 1
    output = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0 if report["metadata_preflight_ready_for_human_review"] else 1


if __name__ == "__main__":
    sys.exit(main())
