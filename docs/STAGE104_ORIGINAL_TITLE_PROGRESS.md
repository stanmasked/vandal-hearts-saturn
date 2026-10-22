# Stage104 — follow real KONAMI splash toward original Saturn title/menu

## Verified original-disc starting point

Stage103 established a decisive A/B result on the user's fully
Stage02-SHA-256-pinned English-v1.1 Track1/Track2/CUE. In the pinned
historical real Yabause with dummy M68K, 600 frames gave 396 numeric
CD callbacks and all-black Titan framebuffer. With C68K enabled in the
same opt-in original game mode, 600 frames gave **997** genuinely
initiated CD reads and a **visibly rendered KONAMI logo**, with
61,440 nonblack RGB pixels.

This **is genuine visual evidence of the original game's splash**;
it does not yet prove the title screen, start menu or first battle.

## Stage104 long-run mode

`tools/patch_yabause_private_long_frames.py` retains the pinned
original public Yabause and C68K mode from Stage103 and changes ONLY
the permitted bounded frame count from 600 to **3600**. It still
captures protected local screenshots and numeric VDP/SH2 checkpoints
at every 120 emulated frames plus the final frame. Its gated original
Yabause ISOCD callback writes numeric-only physical FAD events.

GCC/Clang in public CI use only fabricated ISO/CUE tracks, negative
inputs and public pinned upstream source; the original image and
private frames never leave the operator's local 0700 directory.
Actions can publish the **public emulator executable**, not original
game content.

Private original media execution must be done independently in a fresh
protected folder, with source and executable SHA-256 pinned. A
60–3600 frame count is allowed; 120-frame checkpoints are
informational and need visual inspection to identify transitions.

## Questions to answer

- Does the KONAMI splash disappear and reveal original Vandal Hearts
  title/menu frames within 3600 emulated frames?
- Does the original code continue initiating ISOCD reads as intro
  transitions progress? A video-mode change or ROM file overlap is
  useful context but does not identify a gameplay scene by itself.
- Are there recognizable graphical elements rather than merely
  nonzero output? Visually inspect the **private** PNGs.
- Are there any actual reads within `BATL1PRG.BIN` and
  `MAP_1_1C.BIN` extents, and were they initiated naturally, not
  through Stage98's manual sector probe?

The experiment should preserve false flags for first-battle authenticity
until actual battlefield images and independently synchronized FAD
evidence exist. A title screen alone is not the first tactical map.

## Current status

Stage104 artifact and extended real-disc capture need individual
verification. The code itself does not justify claiming title/menu or
first-battle progression. Issue #11 remains open.
