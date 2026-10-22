#!/usr/bin/env python3
"""Stage99: opt-in bounded Saturn guest emulation on the pinned real Yabause.

This is the genuine CDCORE_ISO/SH2 interpreter and software video core.
No original game content is bundled or put into public CI. It may fail to
boot on historical Yabause; success alone is NOT proof of first-battle play.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from tools.patch_yabause_private_disc_probe import (
    PROBE_CHECK, STAGE98_CONDITION, instrument_probe_runner,
)

MODE = "vh-private-frame-boot"
PASS = "STAGE99_REAL_YABAUSE_BOUND_FRAMES_PASS"
STAGE99_CONDITION = STAGE98_CONDITION.replace(
    'strcmp(argv[1], "vh-private-disc-probe") == 0)))',
    'strcmp(argv[1], "vh-private-disc-probe") == 0))) || '
    '(argc == 4 && strcmp(argv[1], "vh-private-frame-boot") == 0))',
)

BOOT_CHECK = r'''      if (strcmp(argv[1], "vh-private-frame-boot") == 0)
      {
         /* Reinitialize the core, this time with a REAL Saturn CD drive
            backend, emulated BIOS and bounded real SH2 frame execution.
            This command is never invoked on user media from public CI. */
         const char *gate_path = getenv("VH_SATURN_CAPTURE_GATE");
         const char *log_path = getenv("VH_SATURN_FAD_LOG");
         const char *private_dir = getenv("VH_SATURN_PRIVATE_FRAMES_DIR");
         int frames = 0;
         char pre_path[1024], post_path[1024], stats_path[1024];
         pixel_t *pixels = NULL;
         int width = 0, height = 0;
         sh2regs_struct before = { 0 }, after = { 0 };
         int progress = 0;
         if (argc != 4 || !gate_path || !*gate_path || !log_path ||
             !*log_path || !private_dir || !*private_dir ||
             sscanf(argv[3], "%d", &frames) != 1 ||
             frames < 1 || frames > 120 ||
             snprintf(pre_path, sizeof(pre_path), "%s/pre.png", private_dir)
                 >= (int)sizeof(pre_path) ||
             snprintf(post_path, sizeof(post_path), "%s/post.png", private_dir)
                 >= (int)sizeof(post_path) ||
             snprintf(stats_path, sizeof(stats_path), "%s/frames.stats", private_dir)
                 >= (int)sizeof(stats_path))
         {
            YabauseDeInit();
            return 201;
         }
         YabauseDeInit();
         yabauseinit_struct source_game = { 0 };
         source_game.percoretype = PERCORE_DUMMY;
         source_game.sh2coretype = SH2CORE_INTERPRETER;
         source_game.vidcoretype = VIDCORE_SOFT;
         source_game.m68kcoretype = M68KCORE_DUMMY;
         source_game.sndcoretype = SNDCORE_DUMMY;
         source_game.cdcoretype = CDCORE_ISO;
         source_game.carttype = CART_NONE;
         source_game.regionid = REGION_AUTODETECT;
         source_game.biospath = NULL;  /* Yabause high-level BIOS emulation */
         source_game.cdpath = argv[2];
         source_game.buppath = NULL;
         source_game.mpegpath = NULL;
         source_game.cartpath = NULL;
         source_game.frameskip = 0;
         source_game.videoformattype = VIDEOFORMATTYPE_NTSC;
         source_game.clocksync = 0;
         source_game.basetime = 0;
         source_game.skip_load = 0;
         source_game.numthreads = 0;
         source_game.usethreads = 0;
         /* Open manual read gate before boot. Core CD callbacks alone
            write VHCD_FAD values; no resource bytes enter the log. */
         FILE *gate = fopen(gate_path, "wb");
         if (!gate || fputs("1\n", gate) < 0 || fclose(gate) != 0)
            return 202;
         if (YabauseInit(&source_game) != 0)
            return 203;
         if (!MSH2)
         {
            YabauseDeInit();
            return 204;
         }
         SH2GetRegisters(MSH2, &before);
         TitanGetResolution(&width, &height);
         if (width <= 0 || height <= 0 || width > 704 || height > 512)
         {
            YabauseDeInit();
            return 205;
         }
         pixels = (pixel_t*)calloc(704U * 512U, sizeof(pixel_t));
         if (!pixels)
         {
            YabauseDeInit();
            return 206;
         }
         TitanRender(pixels);
         if (lodepng::encode(pre_path, (unsigned char*)pixels,
                             width, height) != 0)
         {
            free(pixels);
            YabauseDeInit();
            return 207;
         }
         for (int frame = 0; frame < frames; ++frame)
         {
            if (YabauseEmulate() != 0)
            {
               free(pixels);
               YabauseDeInit();
               return 208;
            }
            progress++;
         }
         SH2GetRegisters(MSH2, &after);
         TitanGetResolution(&width, &height);
         if (width <= 0 || height <= 0 || width > 704 || height > 512)
         {
            free(pixels);
            YabauseDeInit();
            return 209;
         }
         TitanRender(pixels);
         if (lodepng::encode(post_path, (unsigned char*)pixels,
                             width, height) != 0)
         {
            free(pixels);
            YabauseDeInit();
            return 210;
         }
         free(pixels);
         if (remove(gate_path) != 0)
         {
            YabauseDeInit();
            return 211;
         }
         FILE *stats = fopen(stats_path, "wb");
         if (!stats ||
             fprintf(stats, "STAGE99_FRAMES %d\nSTAGE99_PC_BEFORE %u\n"
                            "STAGE99_PC_AFTER %u\nSTAGE99_WIDTH %d\n"
                            "STAGE99_HEIGHT %d\n",
                     progress, before.PC, after.PC, width, height) < 0 ||
             fclose(stats) != 0)
         {
            YabauseDeInit();
            return 212;
         }
         YabauseDeInit();
         puts("STAGE99_REAL_YABAUSE_BOUND_FRAMES_PASS");
         return 0;
      }
'''


def instrument_boot_runner(raw: bytes) -> bytes:
    code = instrument_probe_runner(raw).decode("utf-8")
    if (code.count(STAGE98_CONDITION) != 1 or
            code.count(PROBE_CHECK) != 1 or MODE in code or PASS in code or
            STAGE99_CONDITION == STAGE98_CONDITION):
        raise ValueError("unrecognized pinned Stage98 runner layout")
    code = code.replace(STAGE98_CONDITION, STAGE99_CONDITION)
    code = code.replace(PROBE_CHECK, BOOT_CHECK + "\n" + PROBE_CHECK)
    if (code.count(PASS) != 1 or
            code.count('strcmp(argv[1], "vh-private-frame-boot")') != 2 or
            code.count("YabauseEmulate()") != 2 or
            code.count("source_game.cdpath = argv[2];") != 1):
        raise ValueError("incomplete Stage99 game-frame mode")
    return code.encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        if (args.source.resolve() == args.output.resolve() or
                args.output.exists() or args.source.name != "yui.cpp" or
                args.output.suffix != ".cpp"):
            raise ValueError("unexpected pinned runner path")
        data = instrument_boot_runner(args.source.read_bytes())
        with args.output.open("xb") as out:
            out.write(data)
    except (OSError, ValueError, TypeError, UnicodeError):
        print("STAGE99_PINNED_GAME_FRAME_BOOT_PATCH_REJECTED", file=sys.stderr)
        return 1
    print("STAGE99_PUBLIC_YABAUSE_FRAME_BOOT_INSTRUMENTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
