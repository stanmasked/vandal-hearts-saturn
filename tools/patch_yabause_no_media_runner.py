#!/usr/bin/env python3
"""Stage82: inject an opt-in *no-media* Yabause initialization smoke mode.

Only a specific pinned, publicly licensed upstream runner source is accepted.
No game media is loaded and no generic patching of arbitrary files is allowed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.check_yabause_upstream_callback import git_blob_sha

UPSTREAM_YUI_BLOB = "fd97788d53703bcfe2f4bd2d1c1c8333e2699a11"
MAIN_ANCHOR = "int main(int argc, char *argv[])\n{\n"
MODE_NAME = "vh-no-media-init"
SUCCESS = "STAGE82_REAL_YABAUSE_INIT_NO_MEDIA_PASS"

INJECTION = r'''   /* Stage82: test real upstream system init, without media or BIOS. */
   if (argc == 2 && strcmp(argv[1], "vh-no-media-init") == 0)
   {
      yabauseinit_struct yinit = { 0 };
      yinit.percoretype = PERCORE_DUMMY;
      yinit.sh2coretype = SH2CORE_INTERPRETER;
      yinit.vidcoretype = VIDCORE_SOFT;
      yinit.m68kcoretype = M68KCORE_DUMMY;
      yinit.sndcoretype = SNDCORE_DUMMY;
      yinit.cdcoretype = CDCORE_DUMMY;
      yinit.carttype = CART_NONE;
      yinit.regionid = REGION_AUTODETECT;
      yinit.biospath = NULL;
      yinit.cdpath = NULL;
      yinit.buppath = NULL;
      yinit.mpegpath = NULL;
      yinit.cartpath = NULL;
      yinit.frameskip = 0;
      yinit.videoformattype = VIDEOFORMATTYPE_NTSC;
      yinit.clocksync = 0;
      yinit.basetime = 0;
      yinit.skip_load = 1;
      if (YabauseInit(&yinit) != 0)
      {
         fputs("STAGE82_REAL_YABAUSE_INIT_NO_MEDIA_FAIL\n", stderr);
         return 92;
      }
      YabauseDeInit();
      puts("STAGE82_REAL_YABAUSE_INIT_NO_MEDIA_PASS");
      return 0;
   }
'''


def instrument_runner(original: bytes) -> bytes:
    if not isinstance(original, bytes) or git_blob_sha(original) != UPSTREAM_YUI_BLOB:
        raise ValueError("runner does not match pinned public Yabause Git blob")
    source = original.decode("utf-8")
    if source.count(MAIN_ANCHOR) != 1 or MODE_NAME in source:
        raise ValueError("unexpected original runner main layout")
    index = source.index(MAIN_ANCHOR) + len(MAIN_ANCHOR)
    return (source[:index] + INJECTION + source[index:]).encode("utf-8")


def patch_runner(source: Path, destination: Path) -> dict:
    if source.resolve() == destination.resolve() or destination.exists():
        raise ValueError("refusing overwrite")
    if source.name != "yui.cpp" or destination.suffix != ".cpp":
        raise ValueError("unexpected source or output name")
    output = instrument_runner(source.read_bytes())
    with destination.open("xb") as f:
        f.write(output)
    return {
        "public_upstream_runner_pinned": True,
        "no_game_media_used": True,
        "no_bios_loaded": True,
        "smoke_mode": MODE_NAME,
        "init_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(patch_runner(args.source, args.output), sort_keys=True))
        return 0
    except (OSError, ValueError, UnicodeError, TypeError):
        print("STAGE82_PINNED_YABAUSE_RUNNER_PATCH_REJECTED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
