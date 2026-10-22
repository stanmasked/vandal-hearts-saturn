# Stage107 — real Saturn START button after original title

## Ground truth before input

The complete privately restored English-v1.1 Saturn Track1, Track2 and
CUE matched Stage02 full hashes. Pinned genuine historical Yabause with
SH2, HLE BIOS, C68K and actual ISOCD played the original KONAMI and
introductory film and produced an actual title image at emulated
frame 12,000:

**VANDAL HEARTS / The Lost Civilization / V1.1 / Press START Button.**

The 12,000-frame local diagnostic used an immediate-only frame-cap
patch of an officially built public Yabause executable. It completed
12,000/12,000 original-game frames, captured 19,883 naturally
triggered numeric FAD callback reads and left original input media
unchanged. It **did not press START**.

## What changes in Stage107

`tools/patch_yabause_private_start_pad.py` is chained to the exact
pinned public Stage106 real-title build. All original SH2/C68K,
CDCORE_ISO, VDP renderer and protected numeric/video witnesses are
unchanged. Only the private game mode grows to 13,200 frames and
attaches one real **standard Saturn pad to port 1** through the
historical public Yabause `PerPadAdd(&PORTDATA1)`.

Both control and experimental processes connect exactly the same
controller. Optional environment variable
`VH_SATURN_START_AT_FRAME` selects an actual emulated frame index
between 12,000 and the requested end minus eight; the experiment
calls `PerPadStartPressed(pad)` immediately **before**
`YabauseEmulate()` at the requested frame and
`PerPadStartReleased(pad)` **six frames later**. The baseline
never calls either press/release method.

A 0600 protected local `pad-events.txt` stores only numerical
frame labels and the control/experiment mode, never source game
contents. All original BIN/CUE, original image frames, CD FAD logs
and SH2 instruction words remain within the private 0700 folder.

## Required private A/B execution

Use two newly created **distinct** private 0700 directories and the
same independently hash-pinned Stage107 GCC/Clang public executable.
Verify all three original source Stage02 digests before/after
each process. Both runs must request exactly 13,200 frames.

First run, **control** — omit the environment variable:

```bash
VH_SATURN_CAPTURE_GATE=/private/control/gate \
VH_SATURN_FAD_LOG=/private/control/fad.vhcdlog \
VH_SATURN_PRIVATE_FRAMES_DIR=/private/control \
  /private/pinned-public-yabause vh-private-frame-boot \
  /private/original-saturn.cue 13200
```

Second run, **START pulse** at frame 12060:

```bash
VH_SATURN_START_AT_FRAME=12060 \
VH_SATURN_CAPTURE_GATE=/private/pressed/gate \
VH_SATURN_FAD_LOG=/private/pressed/fad.vhcdlog \
VH_SATURN_PRIVATE_FRAMES_DIR=/private/pressed \
  /private/pinned-public-yabause vh-private-frame-boot \
  /private/original-saturn.cue 13200
```

These are illustrative placeholders, not the user's actual paths.
Execute with `umask 077`; never export source assets or frame images
through GitHub Actions.

The experiment passes the controller-integrity test if:
- Both processes finish on the same original-game media;
- The no-START control has `VH_PAD mode=0` and no button events;
- The input run has exactly one START press and release, at 12060
  and 12066, and `VH_PAD mode=1`;
- The snapshots and numeric CD callbacks are compared beginning
  with frame 12000, NOT just at process start;
- The resulting game scene is visually identified **in private**.

`VH_PAD` events demonstrate that the emulator code was asked to
present the button state, not that the original Saturn game recognized
it. A visually observed menu transition plus a changed guest input/
FAD timeline would be stronger evidence.

The first tactical encounter remains distinct from the title and menu.
Issue #11 continues OPEN until real battlefield graphics and loader/
combat behavior are independently verified.
