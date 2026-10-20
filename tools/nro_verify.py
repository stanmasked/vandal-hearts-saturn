#!/usr/bin/env python3
"""Inspect a ROM-free homebrew Nintendo Switch .nro header without executing it.

Structural acceptance is not an emulator or console runtime test.  This tool
must not be treated as a security validator of untrusted executables.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

HEADER_BYTES = 0x80
MAGIC_OFFSET = 0x10
MAX_NRO_BYTES = 512 * 1024 * 1024


def inspect_nro(path: Path) -> dict:
    size = path.stat().st_size
    if size < HEADER_BYTES or size > MAX_NRO_BYTES:
        raise ValueError("NRO file size out of bounds")
    with path.open("rb") as handle:
        header = handle.read(HEADER_BYTES)
        if header[MAGIC_OFFSET:MAGIC_OFFSET + 4] != b"NRO0":
            raise ValueError("Missing NRO0 signature at offset 0x10")
        version, executable_size = struct.unpack_from("<II", header, 0x14)
        if executable_size < HEADER_BYTES or executable_size > size:
            raise ValueError("Invalid executable NRO size in header")
        names = ("text", "rodata", "data")
        segments = {}
        for index, name in enumerate(names):
            offset, length = struct.unpack_from("<II", header, 0x20 + 8 * index)
            if length and (offset < HEADER_BYTES or offset + length > executable_size):
                raise ValueError(f"{name} segment outside NRO body")
            segments[name] = {"offset": offset, "bytes": length}
        if not segments["text"]["bytes"]:
            raise ValueError("Empty NRO code segment")
        has_assets = False
        if size > executable_size:
            handle.seek(executable_size)
            has_assets = handle.read(4) == b"ASET"
            if not has_assets:
                raise ValueError("Unrecognized trailing data instead of ASET")
        handle.seek(0)
        checksum = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return {
        "format": "NRO0", "version": version, "file_bytes": size,
        "executable_bytes": executable_size, "has_homebrew_assets": has_assets,
        "segments": segments, "sha256": checksum.hexdigest(),
        "limitations": "Structural validation only; no Switch or emulator execution verified.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nro", type=Path)
    parser.add_argument("--output", type=Path, help="Optional JSON metadata report")
    args = parser.parse_args()
    report = json.dumps(inspect_nro(args.nro), indent=2) + "\n"
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
