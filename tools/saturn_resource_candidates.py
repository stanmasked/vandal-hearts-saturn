#!/usr/bin/env python3
"""Stage 17: metadata-only crosswalk of candidate Saturn resource bundles.

This reads only ISO9660 directory metadata. Matching names and contiguous
extents are leads for private investigation, not proof of runtime relationships.
No file payloads, hashes, pixels, audio or original game bytes are emitted.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from tools.saturn_iso import SaturnISO

ISO_USER_SECTOR_BYTES = 2048
MAP_FAMILIES = {
    "M_MAP": re.compile(r"^M_MAP\d+\.MAP$", re.I),
    "M_IVE": re.compile(r"^M_IVE\d+\.MAP$", re.I),
    "M_KEY": re.compile(r"^M_KEY\d+\.MAP$", re.I),
}
CANDIDATE_GROUPS = (
    ("numbered_scene_assets_1_1", ("MAP_1_1C.BIN", "MAP_1_1P.BIN"),
     "Shared MAP_1_1 stem and adjacent ISO extents; suffix roles unverified."),
    ("battle_program_candidates", ("BATL1PRG.BIN", "BATLEPRG.BIN"),
     "Similar battle-program names and adjacent ISO extents; runtime use unverified."),
    ("event_index_01_candidates", ("EV01.PRG", "EVENT01.DAT"),
     "Matching numeric token only; loader relationship unverified."),
    ("map_index_01_candidate", ("M_MAP01.MAP",),
     "Filename/index candidate only; not proven to be the first battle map."),
)


def _normalize_entries(entries):
    if not isinstance(entries, list):
        raise ValueError("Expected ISO file-entry list")
    by_name = {}
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("Malformed ISO file entry")
        name = item.get("name")
        lba, size = item.get("lba"), item.get("bytes")
        if not isinstance(name, str) or not name or "/" in name or "\\" in name:
            raise ValueError("Unsafe or empty ISO filename")
        if (not isinstance(lba, int) or isinstance(lba, bool) or lba < 0 or
                not isinstance(size, int) or isinstance(size, bool) or size <= 0):
            raise ValueError("Invalid ISO extent or file size")
        key = name.upper()
        if key in by_name:
            raise ValueError("Duplicate case-insensitive ISO filename")
        sectors = (size + ISO_USER_SECTOR_BYTES - 1) // ISO_USER_SECTOR_BYTES
        by_name[key] = {
            "name": name, "size_bytes": size, "extent_lba": lba,
            "iso_sectors": sectors, "extent_end_exclusive": lba + sectors,
        }
    return by_name


def _candidate_group(by_name, group_name, expected_names, rationale):
    found = [by_name[n.upper()] for n in expected_names if n.upper() in by_name]
    found.sort(key=lambda entry: (entry["extent_lba"], entry["name"].upper()))
    missing = [n for n in expected_names if n.upper() not in by_name]
    contiguous = None
    if not missing and len(found) > 1:
        contiguous = all(a["extent_end_exclusive"] == b["extent_lba"]
                         for a, b in zip(found, found[1:]))
    return {
        "group": group_name,
        "expected_names": list(expected_names),
        "present_files": found,
        "missing_names": missing,
        "extents_contiguous_in_iso": contiguous,
        "association_basis": rationale,
        "runtime_relationship_verified": False,
    }


def analyze_entries(entries, *, product_code=None, volume_id=None,
                    source_label="unverified"):
    by_name = _normalize_entries(entries)
    files = list(by_name.values())
    maps = [e for e in files if e["name"].upper().endswith(".MAP")]
    family_counts = Counter()
    for entry in maps:
        name = entry["name"].upper()
        matched = next((family for family, pattern in MAP_FAMILIES.items()
                        if pattern.fullmatch(name)), None)
        if matched:
            family_counts[matched] += 1
        elif name == "M_SHOW.MAP":
            family_counts["M_SHOW"] += 1
        else:
            family_counts["OTHER_MAP"] += 1
    sizes = Counter(str(e["size_bytes"]) for e in maps)
    return {
        "schema": 1,
        "kind": "SATURN_ISO_RESOURCE_CANDIDATE_CROSSWALK",
        "source": {
            "product_code": product_code,
            "volume_id": volume_id,
            "operator_source_label": source_label,
            "version_authenticated_by_iso_metadata": False,
        },
        "inventory": {
            "file_count": len(files),
            "map_file_count": len(maps),
            "map_family_counts": dict(sorted(family_counts.items())),
            "map_size_bytes_counts": dict(sorted(sizes.items(), key=lambda pair: int(pair[0]))),
        },
        "candidate_groups": [
            _candidate_group(by_name, name, expected, rationale)
            for name, expected, rationale in CANDIDATE_GROUPS
        ],
        "limitations": [
            "Names, numeric suffixes, file sizes and contiguous ISO extents do not prove loader relationships.",
            "Candidate MAP record fields are not authenticated tile coordinates, terrain, height or collision.",
            "This report excludes all file payloads, hashes, graphics, audio and executable contents.",
            "The English v1.1 source is translation-patched; Japanese-master equivalence is unverified.",
        ],
    }


def analyze_disc(track1: Path, *, source_label="unverified"):
    fs = SaturnISO(track1).inspect(include_files=True)
    return analyze_entries(fs["file_entries"],
                           product_code=fs.get("boot_product_code"),
                           volume_id=fs.get("volume_id"),
                           source_label=source_label)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track1", type=Path, help="Private owned Saturn RAW MODE1/2352 Track 1")
    parser.add_argument("--source-label", default="unverified",
                        help="Operator-provided label; ISO metadata does not authenticate it")
    parser.add_argument("--output", type=Path, help="Write metadata-only JSON report")
    args = parser.parse_args()
    result = json.dumps(analyze_disc(args.track1, source_label=args.source_label),
                        indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
