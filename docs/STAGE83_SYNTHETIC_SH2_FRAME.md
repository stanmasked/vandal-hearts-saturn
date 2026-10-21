# Stage83 — one synthetic SH-2 frame in the genuine pinned Yabause runner

Stage82 validated actual `YabauseInit` and `YabauseDeInit` without
original media. Stage83 tests a higher evidence bar: execute **one real
Yabause emulation frame** and independently verify that invented SH-2
instructions actually changed an emulated register.

## Public, reproducible inputs

- Fixed public Yabause commit: `7e38821dbac265490f115e163c523a939acda759`.
- The pinned upstream `cdbase.c` Git blob is checked by Stage80's full
  source patcher. The runner `yui.cpp` Git blob is verified against
  `fd97788d53703bcfe2f4bd2d1c1c8333e2699a11`.
- The runner's missing LodePNG dependency is fetched from a fixed
  public commit with verified file blob IDs, as in Stage81.
- The `vh-synthetic-sh2-frame` mode is inserted only after verifying
  the entire original runner source. Unrecognized source/layout drift
  fails closed. Existing outputs are never overwritten by the patcher.
- GCC and Clang independently build and link the **real Yabause runner**,
  then run it with no BIOS or Saturn disc image.

## Synthetic test program

Write three hand-authored SH-2 instructions into empty Saturn high work
RAM at `0x06000000`, verify the readback, and set the master SH-2 PC to
that location:

| Address | Instruction word | SH-2 meaning |
|---|---|---|
| 0x06000000 | 0x7001 | ADD #1, R0 |
| 0x06000002 | 0xAFFD | BRA back to 0x06000000 |
| 0x06000004 | 0x0009 | NOP (branch delay slot) |

Before running, set R0=0 and mask normal interrupts. Call the real
`YabauseEmulate()` **once**, then read back SH-2 registers and require
R0 to have incremented and PC to remain in the tiny synthetic loop.
The executable must exit cleanly after `YabauseDeInit` and emit the
strict receipt `STAGE83_REAL_YABAUSE_SYNTHETIC_SH2_FRAME_PASS`.

CI limits the subprocess to 20 seconds, with a forced-kill allowance,
and requires a zero exit code. The smoke uses `CDCORE_DUMMY`,
`biospath=NULL`, `cdpath=NULL`, and `skip_load=1`. This is **not**
a bootable Saturn program or a simulation of an original game level.

## Evidence boundary and privacy

A green result would prove that real Yabause can execute this synthetic
SH-2 loop while advancing one emulated frame using core timing/CPU
paths. It would not prove correctness of authentic Saturn disc loading,
CD sector addresses, original map resources, story, graphics, sound,
battle rules, or the source's Japanese/English edition equivalence.

No original Saturn ISO/BIN/CUE, BIOS, sprite, music, screenshot or
user private capture is used or uploaded. The separate evidence milestone
for the first authentic battle remains Issue #11. Third-party emulator
code stays in temporary CI workspaces; its license must be respected
for any eventual binary redistribution.
