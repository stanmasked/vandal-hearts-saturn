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
        previous_end = 0
        for index, name in enumerate(names):
            offset, length = struct.unpack_from("<II", header, 0x20 + 8 * index)
            # NRO segment offsets are measured from the start of the executable.
            # In real elf2nro output .text commonly starts at offset ZERO and
            # contains the first 0x80 bytes, including the NRO0 header.
            # Do not impose an artificial 0x80 minimum on segment offsets.
            if length:
                if offset < previous_end:
                    raise ValueError(f"{name} segment overlaps previous segment")
                if offset + length > executable_size:
                    raise ValueError(f"{name} segment outside NRO body")
                previous_end = offset + length
            segments[name] = {"offset": offset, "bytes": length}
        if not segments["text"]["bytes"]:
            raise ValueError("Empty NRO code segment")
        if (segments["text"]["offset"] > 0 or
                segments["text"]["bytes"] <= HEADER_BYTES):
            raise ValueError("NRO .text must contain the start header and executable code")
        has_assets = False
        if size > executable_size:
            handle.seek(executable_size)
            asset_header = handle.read(0x38)
            if len(asset_header) < 0x38 or asset_header[:4] != b"ASET":
                raise ValueError("Invalid or truncated trailing ASET header")
            asset_version, = struct.unpack_from("<I", asset_header, 4)
            if asset_version != 0:
                raise ValueError("Unsupported ASET version")
            for index, label in enumerate(("icon", "nacp", "romfs")):
                asset_offset, asset_size = struct.unpack_from("<QQ", asset_header,
                                                             8 + 16 * index)
                if asset_size and (asset_offset < 0x38 or
                                   asset_offset + asset_size > size - executable_size):
                    raise ValueError(f"{label} ASET payload out of bounds")
            has_assets = True
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
