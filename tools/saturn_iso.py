#!/usr/bin/env python3
"""Read-only ISO9660 filesystem inventory for Sega Saturn RAW MODE1/2352 track images."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

RAW_SECTOR = 2352
USER_OFFSET = 16
USER_SIZE = 2048
MAX_DIR_SIZE = 32 * 1024 * 1024
MAX_ENTRIES = 20000
SYNC = bytes.fromhex("00ffffffffffffffffffff00")


def both32(data: bytes, pos: int) -> int:
    little = int.from_bytes(data[pos:pos + 4], "little")
    big = int.from_bytes(data[pos + 4:pos + 8], "big")
    if little != big:
        raise ValueError("ISO9660 endian mismatch")
    return little


def iso_name(raw: bytes) -> str:
    if raw in (b"\x00", b"\x01"):
        return raw.decode("ascii")
    name = raw.decode("ascii", errors="replace").split(";", 1)[0]
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ValueError("Unsafe ISO filename")
    return name


class SaturnISO:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.size = self.path.stat().st_size
        if self.size < 17 * RAW_SECTOR or self.size % RAW_SECTOR:
            raise ValueError("Expected complete RAW MODE1/2352 file")
        self.sectors = self.size // RAW_SECTOR

    def sector(self, stream, lba: int) -> bytes:
        if not 0 <= lba < self.sectors:
            raise ValueError("Sector outside image")
        stream.seek(lba * RAW_SECTOR)
        raw = stream.read(RAW_SECTOR)
        if len(raw) != RAW_SECTOR or raw[:12] != SYNC or raw[15] != 1:
            raise ValueError("Invalid RAW MODE1 sector")
        return raw[USER_OFFSET:USER_OFFSET + USER_SIZE]

    @staticmethod
    def record(raw: bytes) -> dict:
        if len(raw) < 34 or raw[0] != len(raw):
            raise ValueError("Malformed directory record")
        length = raw[32]
        if 33 + length > len(raw):
            raise ValueError("Truncated ISO filename")
        return {"name": iso_name(raw[33:33 + length]),
                "lba": both32(raw, 2), "bytes": both32(raw, 10),
                "directory": bool(raw[25] & 0x02)}

    def entries(self, stream, extent: int, length: int) -> list[dict]:
        if length < 0 or length > MAX_DIR_SIZE:
            raise ValueError("Oversized directory")
        sectors = (length + USER_SIZE - 1) // USER_SIZE
        if extent < 0 or extent + sectors > self.sectors:
            raise ValueError("Directory outside image")
        data = b"".join(self.sector(stream, extent + n)
                        for n in range(sectors))[:length]
        at, records = 0, []
        while at < len(data):
            n = data[at]
            if n == 0:
                at = ((at // USER_SIZE) + 1) * USER_SIZE
                continue
            if at % USER_SIZE + n > USER_SIZE or at + n > len(data):
                raise ValueError("Malformed ISO directory boundary")
            item = self.record(data[at:at + n])
            at += n
            if item["name"] in ("\x00", "\x01"):
                continue
            if item["lba"] + (item["bytes"] + USER_SIZE - 1) // USER_SIZE > self.sectors:
                raise ValueError("File extent beyond image")
            records.append(item)
            if len(records) > MAX_ENTRIES:
                raise ValueError("Too many directory records")
        return records

    def inspect(self, include_files: bool = False) -> dict:
        with self.path.open("rb") as stream:
            header = self.sector(stream, 0)
            if not header.startswith(b"SEGA SEGASATURN"):
                raise ValueError("Not a Sega Saturn disc")
            pvd = self.sector(stream, 16)
            if pvd[:7] != b"\x01CD001\x01":
                raise ValueError("ISO9660 primary volume descriptor missing")
            declared = both32(pvd, 80)
            if declared > self.sectors:
                raise ValueError("Declared ISO volume exceeds track")
            root_len = pvd[156]
            root = self.record(pvd[156:156 + root_len])
            if not root["directory"]:
                raise ValueError("Root is not a directory")
            pending = [("", root["lba"], root["bytes"])]
            seen, files, directories = set(), [], 0
            while pending:
                prefix, extent, length = pending.pop()
                if (extent, length) in seen:
                    continue
                seen.add((extent, length))
                directories += 1
                for item in self.entries(stream, extent, length):
                    filename = prefix + item["name"]
                    if item["directory"]:
                        pending.append((filename + "/", item["lba"], item["bytes"]))
                    else:
                        files.append({"name": filename, "lba": item["lba"],
                                      "bytes": item["bytes"]})
                    if len(files) + len(pending) > MAX_ENTRIES:
                        raise ValueError("Too many filesystem records")
            files.sort(key=lambda entry: entry["name"])
            extensions = Counter(entry["name"].rsplit(".", 1)[-1].upper()
                                 if "." in entry["name"] else "<NONE>" for entry in files)
            product = re.search(rb"T-\d{4,6}[A-Z]?", header[:128])
            report = {"format": "Saturn RAW MODE1/2352 / ISO9660",
                      "sectors": self.sectors, "bytes": self.size,
                      "boot_product_code": product.group().decode() if product else None,
                      "volume_id": pvd[40:72].decode("ascii", "replace").rstrip(" \x00"),
                      "declared_iso_sectors": declared,
                      "directories": directories, "files": len(files),
                      "extension_counts": dict(sorted(extensions.items())),
                      "note": "Metadata only. The English v1.1 disc is a patched release."}
            if include_files:
                report["file_entries"] = files
            return report


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("track1", type=Path)
    p.add_argument("--hash", action="store_true")
    p.add_argument("--list-files", action="store_true",
                   help="Include metadata (filenames, LBA, file sizes), not file contents")
    p.add_argument("--json", type=Path, help="Write metadata JSON report")
    args = p.parse_args()
    report = SaturnISO(args.track1).inspect(include_files=args.list_files)
    if args.hash:
        report["sha256"] = sha256_file(args.track1)
    output = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.json:
        args.json.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
