#!/usr/bin/env python3
"""Read-only inventory of an owned multi-track Saturn CUE/BIN (no copyrighted content exported)."""
import argparse
import hashlib
import json
import re
from pathlib import Path

FILE = re.compile(r'^\s*FILE\s+(?:"([^"]+)"|(\S+))\s+(BINARY|WAVE|MOTOROLA|AIFF|MP3)\s*$', re.I)
TRACK = re.compile(r'^\s*TRACK\s+(\d+)\s+(\S+)\s*$', re.I)


def scan(cue: Path) -> dict:
    tracks = []
    files = []
    current = None
    for raw in cue.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if match := FILE.match(raw):
            filename = match.group(1) or match.group(2)
            candidate = (cue.parent / filename).resolve()
            if not candidate.is_relative_to(cue.parent.resolve()):
                raise ValueError("CUE paths must remain inside directory of CUE file")
            current = candidate
            files.append((filename, candidate, match.group(3).upper()))
        elif match := TRACK.match(raw):
            if current is None:
                raise ValueError("TRACK before FILE")
            tracks.append({"number": int(match.group(1)), "mode": match.group(2), "file": current.name})
    result_files = []
    for filename, path, encoding in files:
        if not path.is_file():
            raise FileNotFoundError(f"Missing track file: {filename}")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        result_files.append({"name": path.name, "encoding": encoding,
                             "size_bytes": path.stat().st_size, "sha256": digest.hexdigest()})
    return {"cue": cue.name, "tracks": tracks, "files": result_files,
            "note": "Metadata only; original disc media are never copied into repository."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cue", type=Path)
    args = parser.parse_args()
    print(json.dumps(scan(args.cue.resolve()), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
