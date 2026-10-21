#!/usr/bin/env python3
"""Stage78: integrate pinned PUBLIC Yabause ISO callback with invented sectors.

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
EXPECTED_LOG = "VHCD_FAD 152\nVHCD_FAD 153\n"


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
    callback = extract_patched_callback(real_source)
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
