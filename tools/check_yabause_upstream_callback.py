#!/usr/bin/env python3
"""Stage79: verify original upstream Yabause ISO callback with primary-data read checks.

Fetches only the pinned GPL Yabause *source code* (not a Saturn game), verifies
its Git blob SHA-1, applies our gated capture patch, then compiles and runs the
real extracted callback inside an invented standalone C track fixture.
It is not a build of Yabause itself or a boot of the original game.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.request import urlopen

from tools.saturn_yabause_gated_hook import patch_gated_cdbase
from tools.saturn_yabause_cdbase_hook import FUNCTION, FOLLOWING

UPSTREAM_COMMIT = "7e38821dbac265490f115e163c523a939acda759"
UPSTREAM_BLOB = "d56d5dd1941b553c0ede111a83fcf8e50dbecb45"
UPSTREAM_URL = ("https://raw.githubusercontent.com/Yabause/yabause/" +
                UPSTREAM_COMMIT + "/yabause/src/cdbase.c")
MAX_SOURCE_BYTES = 160_000
RECEIPT = "VH_UPSTREAM_ISO_CALLBACK_TEST_PASS"
EXPECTED_LOG = "VHCD_FAD 152\nVHCD_FAD 153\nVHCD_FAD 200\nVHCD_FAD 300\nVHCD_FAD 400\n"


def git_blob_sha(data: bytes) -> str:
    if not isinstance(data, bytes):
        raise TypeError("expected source bytes")
    return hashlib.sha1(
        ("blob " + str(len(data)) + "\0").encode("ascii") + data
    ).hexdigest()


def validate_upstream_source(raw: bytes) -> str:
    if not isinstance(raw, bytes) or not 1000 <= len(raw) <= MAX_SOURCE_BYTES:
        raise ValueError("untrusted upstream source length")
    if git_blob_sha(raw) != UPSTREAM_BLOB:
        raise ValueError("pinned upstream Git blob mismatch")
    return raw.decode("utf-8")


def extract_patched_callback(source: str) -> str:
    # patch_gated_cdbase internally applies Stage76's exact-anchor patch,
    # which is deliberately fail-closed when the upstream layout drifts.
    output = patch_gated_cdbase(source)
    if output.count("VH_SATURN_CAPTURE_GATE") != 1:
        raise ValueError("gated patch must be present only once")
    start = output.index(FUNCTION)
    end = output.index(FOLLOWING, start + len(FUNCTION))
    fragment = output[start:end]
    # Fail if injected code leaks outside the callback, or fields are missing.
    if (fragment.count("VHCD_FAD %u") != 1 or
            "if (num_read > 0)" not in fragment or
            "vh_first == '1' && vh_second == '\\n' && vh_third == EOF"
            not in fragment):
        raise ValueError("unexpected instrumented callback layout")
    return fragment



def extract_primary_read_callback(source: str) -> str:
    """Fail-closed Stage79 specialization for the exact pinned upstream callback.

    Older Yabause overwrites num_read when reading auxiliary CD subcode, even
    if the primary 2352-byte read failed. The numeric FAD trace must describe
    primary sector-data reads, not the outcome of a later subcode read.
    """
    callback = extract_patched_callback(source)
    marker = "   size_t num_read = 0;"
    if callback.count(marker) != 1 or "vh_primary_read" in callback:
        raise ValueError("unexpected upstream read-variable layout")
    newline = "\r\n" if "\r\n" in callback else "\n"
    callback = callback.replace(marker, marker + newline + "   size_t vh_primary_read = 0;")
    data_reads = (
        ("num_read = fread(buffer, 2352, 1, track->fp);", 3),
        ("num_read = fread(buffer, 2448, 1, track->fp);", 1),
        ("num_read = fread((char *)buffer + 0x10, 2048, 1, track->fp);", 1),
    )
    for target, count in data_reads:
        if callback.count(target) != count:
            raise ValueError("pinned Yabause data-read layout changed")
        callback = callback.replace(target, "vh_primary_read = (" + target[:-1] + ");")
    gate = "if (num_read > 0)"
    if callback.count(gate) != 1:
        raise ValueError("unexpected primary read-gate layout")
    callback = callback.replace(gate, "if (vh_primary_read == 1)")
    return callback


def harness(callback: str) -> str:
    """A C stub for upstream callback types; no original Saturn code/data."""
    if not isinstance(callback, str) or callback.count(FUNCTION) != 1:
        raise ValueError("callback shape mismatch")
    prefix = r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <stdint.h>
typedef uint32_t u32;
typedef uint16_t u16;
typedef uint8_t u8;
typedef struct track_info_struct {
    u32 fad_start;
    u32 fad_end;
    FILE *fp;
    FILE *sub_fp;
    long file_offset;
    int sector_size;
    int interleaved_sub;
} track_info_struct;
typedef struct {
    int track_num;
    track_info_struct track[1];
} session_info_struct;
static struct {
    int session_num;
    session_info_struct *session;
} disc;
static const unsigned char syncHdr[12] = {0};
#define CDLOG(message) ((void)(message))
'''
    suffix = r'''
int main(void) {
    const char *gate_path = getenv("VH_SATURN_CAPTURE_GATE");
    const char *trace_path = getenv("VH_SATURN_FAD_LOG");
    if (!gate_path || !trace_path) return 10;
    FILE *cd = tmpfile();
    if (!cd) return 11;
    /* Three fabricated raw sectors, FADs 151, 152, and 153. */
    for (int n = 0; n < 3 * 2352; ++n) {
        if (fputc((n * 7) & 255, cd) == EOF) return 12;
    }
    fflush(cd);
    rewind(cd);
    session_info_struct session = {0};
    session.track_num = 1;
    session.track[0].fad_start = 151;
    session.track[0].fad_end = 154;
    session.track[0].sector_size = 2352;
    session.track[0].file_offset = 0;
    session.track[0].fp = cd;
    disc.session_num = 1;
    disc.session = &session;
    unsigned char buffer[2448] = {0};

    /* Success while closed: must NOT log. */
    if (!ISOCDReadSectorFAD(151, buffer)) return 20;
    FILE *gate = fopen(gate_path, "wb");
    if (!gate) return 21;
    if (fputs("1\n", gate) < 0 || fclose(gate)) return 22;
    if (!ISOCDReadSectorFAD(152, buffer)) return 23;

    /* Invalid gate bytes cannot enable numeric capture. */
    gate = fopen(gate_path, "wb");
    if (!gate) return 24;
    if (fputs("1\r\n", gate) < 0 || fclose(gate)) return 25;
    if (!ISOCDReadSectorFAD(153, buffer)) return 26;

    gate = fopen(gate_path, "wb");
    if (!gate) return 27;
    if (fputs("1\n", gate) < 0 || fclose(gate)) return 28;
    if (!ISOCDReadSectorFAD(153, buffer)) return 29;

    /* FAD 154 is in the synthetic track table but past EOF. Yabause
       returns 1 regardless, while the hook must check num_read > 0. */
    if (!ISOCDReadSectorFAD(154, buffer)) return 30;
    if (remove(gate_path) != 0) return 31;
    if (!ISOCDReadSectorFAD(151, buffer)) return 32;

    /* Stage79: missing 2352-byte payload, present 96-byte subcode.
       Upstream num_read is overwritten by the subcode fread, so the old
       hook would wrongly record FAD 200 for this failed primary read. */
    FILE *raw_empty = tmpfile();
    FILE *raw_good = tmpfile();
    FILE *sub_good = tmpfile();
    FILE *iso_good = tmpfile();
    FILE *raw2448 = tmpfile();
    if (!raw_empty || !raw_good || !sub_good || !iso_good || !raw2448) return 33;
    for (int n = 0; n < 2352; ++n) {
        if (fputc(n & 255, raw_good) == EOF) return 34;
    }
    for (int n = 0; n < 96; ++n) {
        if (fputc(n & 255, sub_good) == EOF) return 35;
    }
    for (int n = 0; n < 2048; ++n) {
        if (fputc(n & 255, iso_good) == EOF) return 36;
    }
    for (int n = 0; n < 2448; ++n) {
        if (fputc(n & 255, raw2448) == EOF) return 37;
    }
    fflush(raw_good); fflush(sub_good); fflush(iso_good); fflush(raw2448);
    rewind(raw_good); rewind(sub_good); rewind(iso_good); rewind(raw2448);
    gate = fopen(gate_path, "wb");
    if (!gate) return 38;
    if (fputs("1\n", gate) < 0 || fclose(gate)) return 39;

    session.track[0].fad_start = 200;
    session.track[0].fad_end = 200;
    session.track[0].sector_size = 2448;
    session.track[0].interleaved_sub = 0;
    session.track[0].sub_fp = sub_good;
    session.track[0].fp = raw_empty;
    if (!ISOCDReadSectorFAD(200, buffer)) return 40;
    session.track[0].fp = raw_good;
    if (!ISOCDReadSectorFAD(200, buffer)) return 41;

    /* One fabricated 2048-byte user-data read, plus failed read. */
    session.track[0].fad_start = 300;
    session.track[0].fad_end = 300;
    session.track[0].sector_size = 2048;
    session.track[0].sub_fp = NULL;
    session.track[0].fp = raw_empty;
    if (!ISOCDReadSectorFAD(300, buffer)) return 42;
    session.track[0].fp = iso_good;
    if (!ISOCDReadSectorFAD(300, buffer)) return 43;

    /* Full 2448-byte interleaved payload without external subcode. */
    session.track[0].fad_start = 400;
    session.track[0].fad_end = 400;
    session.track[0].sector_size = 2448;
    session.track[0].fp = raw_empty;
    if (!ISOCDReadSectorFAD(400, buffer)) return 44;
    session.track[0].fp = raw2448;
    if (!ISOCDReadSectorFAD(400, buffer)) return 45;
    if (remove(gate_path) != 0) return 46;
    fclose(raw_empty); fclose(raw_good); fclose(sub_good);
    fclose(iso_good); fclose(raw2448);
    fclose(cd);
    puts("VH_UPSTREAM_ISO_CALLBACK_TEST_PASS");
    return 0;
}
'''
    return prefix + "\n" + callback + "\n" + suffix


def verify(cc: str, *, upstream_source: bytes | None = None) -> dict:
    if not cc or cc.startswith("-") or "/" in cc or "\\" in cc:
        raise ValueError("choose a compiler executable name, not a path")
    if upstream_source is None:
        with urlopen(UPSTREAM_URL, timeout=40) as res:
            upstream_source = res.read(MAX_SOURCE_BYTES + 1)
    real_source = validate_upstream_source(upstream_source)
    callback = extract_primary_read_callback(real_source)
    code = harness(callback)
    with tempfile.TemporaryDirectory(prefix="vh-public-upstream-cd-") as folder:
        root = Path(folder)
        source = root / "upstream_callback.c"
        binary = root / "upstream_callback"
        source.write_text(code, encoding="utf-8")
        build = subprocess.run(
            [cc, "-std=c99", "-Wall", "-Wextra", "-Werror", str(source),
             "-o", str(binary)],
            capture_output=True, text=True, timeout=35,
        )
        if build.returncode:
            raise AssertionError("pinned real Yabause callback compilation failed")
        gate = root / "window.vhgate"
        log = root / "session.vhcdlog"
        import os
        env = dict(os.environ)
        env["VH_SATURN_CAPTURE_GATE"] = str(gate)
        env["VH_SATURN_FAD_LOG"] = str(log)
        run = subprocess.run(
            [str(binary)], env=env, capture_output=True,
            text=True, timeout=20,
        )
        if (run.returncode != 0 or run.stderr or
                run.stdout.strip() != RECEIPT):
            raise AssertionError("pinned real Yabause callback execution failed")
        if log.read_text(encoding="ascii") != EXPECTED_LOG or gate.exists():
            raise AssertionError("real upstream callback leaked off-window reads")
    return {
        "source": "pinned_public_yabause_cdbase_c",
        "upstream_commit": UPSTREAM_COMMIT,
        "upstream_git_blob": UPSTREAM_BLOB,
        "compiled_real_upstream_iso_callback": True,
        "synthetic_cd_sectors_only": True,
        "gated_numeric_fad_receipt": True,
        "closed_and_invalid_gate_suppressed": True,
        "failed_sector_read_suppressed": True,
        "primary_data_reads_not_overwritten_by_subcode": True,
        "synthetic_2048_2352_2448_data_modes_checked": True,
        "original_saturn_game_executed": False,
        "full_yabause_emulator_built": False,
        "authentic_first_battle_data_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc", default="cc",
                        help="C compiler executable (gcc or clang)")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.cc)
        text = json.dumps(result, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        print(text, end="")
        return 0
    except (OSError, UnicodeError, ValueError, TypeError, AssertionError):
        print("PINNED_YABAUSE_CALLBACK_CHECK_REJECTED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
