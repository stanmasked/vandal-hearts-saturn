# Stage82 — actual YabauseInit/DeInit with no Saturn game media

## Purpose

Stage81 built and launched the genuine historical Yabause runner through
its original command-line parser, without a disc or BIOS. Stage82 tests a
strictly stronger boundary: call **YabauseInit** and **YabauseDeInit** in
the genuine runner executable. This initializes Yabause's hardware
subsystems, but does not boot a game or advance gameplay frames.

## Reproducible and private-safe method

- Pin upstream Yabause commit `7e38821dbac265490f115e163c523a939acda759`.
- Require the upstream runner `yabause/src/runner/yui.cpp` Git blob
  `fd97788d53703bcfe2f4bd2d1c1c8333e2699a11`.
- Pin the external LodePNG dependency commit and two Git blobs exactly as
  Stage81 did. Neither upstream project is redistributed in this game repo.
- Generate a temporary patched runner in CI; refuse all non-pinned source,
  existing output paths and in-place modification.
- Add an opt-in `vh-no-media-init` command to original runner's
  `main`, limited to the following original Yabause call contract:
  `CDCORE_DUMMY`, `biospath=NULL`, `cdpath=NULL`,
  `skip_load=1`, interpreter SH2, dummy M68K/sound/input and
  software video, then `YabauseInit` → `YabauseDeInit`.
- Launch it in a fresh temporary directory with no source image, BIOS,
  game assets or input capture. The expected unique receipt is:
  `STAGE82_REAL_YABAUSE_INIT_NO_MEDIA_PASS`.

This code reuses the settings of the upstream runner's existing unit-test
initialization code. The original Yabause `YabauseInit` implementation
returns early when `skip_load` is set, instead of attempting game
quickload. The test does **not** read or write actual Saturn disc sectors.

## Evidence boundaries

Successful Stage82 CI shows that subsystem initialization and teardown
can run with an empty CD and internal BIOS emulation settings; it does
**not** prove original BIOS boot, real CD path operation, sector timing,
proper Saturn gameplay or the original Vandal Hearts first battle.
No game media is added to the public repository. See Issue #11.
