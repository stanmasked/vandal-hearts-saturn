# Stage99 — attempt bounded original Saturn game frames under pinned Yabause

Stage98 successfully executed the genuine public Yabause **ISOCD** callback
against the user's actual Stage02-SHA-256-verified private English-v1.1
CUE and two BIN files. It directly read six physical sectors, including
FAD 150 and the CDDA start, but did **not** execute Saturn game code.

Stage99 introduces a new opt-in `vh-private-frame-boot` mode into the
**same pinned historical public Yabause runner**.

## What changes

The new mode requires a privately staged real CUE, a positive integer
number of frames (maximum 600) and protected local paths for the gated
numeric CD-read log and frame files. It deinitializes the Stage82 dummy
test core, initializes a new Yabause instance with
`CDCORE_ISO`, `SH2CORE_INTERPRETER`, `VIDCORE_SOFT`,
`skip_load=0` and the Yabause HLE BIOS (no commercial BIOS included).
It asks the actual `YabauseEmulate()` callback to execute exactly
the requested number of frames, reads SH-2 registers before/after,
and attempts to render two **private** framebuffer images:
`pre.png` before the frames and `post.png` afterward. It writes a
strictly numerical `frames.stats` with frame count, PC-before, PC-after
and framebuffer dimensions and uses the Stage79 real gated CD callback
for `VHCD_FAD` numeric reads.

The instrumented frontend saves an additional private PNG checkpoint at
every 120th frame (120, 240, 360, 480 and 600 when reached). These
checkpoints allow pixel-level comparisons as the Saturn title changes video
modes without treating black pixels as a successfully observed title screen.

### First private original-disc results

A public-only GCC Yabause runner artifact was executed locally, after
verifying the original Track1/Track2/CUE Stage02 SHA-256 pins:
- **12 frames, exit 0**, 53 numeric CD reads, SH2 program counter changed,
  320×224 PNGs completely black.
- **120 frames, exit 0**, 305 numeric CD reads (279 distinct) over physical
  FAD 150–2664, SH2 PC changed, video resolution 352×240 and both
  screenshots entirely black.
- None of those 305 automatically recorded physical CD reads overlapped
  the source filesystem candidate ranges BATL1PRG.BIN (2479–2598) or
  MAP_1_1C.BIN (76486–76527), or Track2 CDDA. The Stage98 diagnostic
  *deliberately* read these addresses and must not be misclassified as
  a real game-loader access.

This confirms an actual original-media-backed emulator frame loop but
**not a visible game/menu/first battle**, and establishes a concrete reason
to probe longer runs and rendering behavior.

The build remains pinned to the historical Yabause and LodePNG public
commits. Synthetic GCC and Clang CI run inherited Stage81–91 tests and
check that the new game mode rejects missing arguments, without booting
the original game or shipping its assets into GitHub.

## Private execution boundary

The original BIN/CUE files, screenshots, frame stats and FAD log must
stay **outside public GitHub and Actions**. The public CI artifact
contains only the GPL-licensed upstream-derived instrumented runner.
A separate, hash-verified executable is then run in a restricted local
private directory. An external wall-clock timeout should enforce
bounded execution.

One suggested form, once all original source SHA-256 pins are verified:

```bash
VH_SATURN_CAPTURE_GATE=/private/capture/gate \
VH_SATURN_FAD_LOG=/private/capture/fad.vhcdlog \
VH_SATURN_PRIVATE_FRAMES_DIR=/private/capture \
/absolute/pinned/public-yabause vh-private-frame-boot \
  /private/original-disc.cue 12
```

This is a sample with placeholder paths. Do **not** copy real BIN/CUE
or captured frames to Actions or PR comments.

## Strong evidence boundary

A successful frame loop would show genuine emulator frame execution
and **private** framebuffer files. It would **not** prove a menu was
visible, that game logic progressed, or that the first battle loaded.
Even an emulator PC value may remain unchanged during legitimate loops.
The screen must be visually inspected and aligned to numeric CD reads
before Issue #11 can be accepted.

A failed initialization or graphics render is a diagnostic result, not
a successful game boot; it should be recorded precisely and investigated.
The existing Stage98 original-disc read-only ISOCD probe remains a
separate, successful milestone.
