# Stage103 — isolate M68K sound-CPU availability during the original Saturn boot

## Why a controlled experiment is needed

The Stage02-verified original English v1.1 Saturn image boots partway
into a genuine public pinned Yabause SH2+CDCORE_ISO execution path.
Real Stage101 and Stage102 private measurements found:

- 305 naturally generated CD FAD callbacks at 120 frames, 396 by
  frame 240 and no new CD reads by frame 600;
- TVMD display enabled, BGON=19 and populated VDP1/VDP2/color RAM,
  but still **zero nonblack pixels** in the video output;
- sampled SH2 PC at `0x06034198` from frame 240 to 600, where the
  locally read opcode classes are **decrement-and-test / conditional
  backward branch**; R0 varies at frame boundaries. The processor
  is executing a software delay loop, not necessarily halted.

The previous opt-in game mode configured `M68KCORE_DUMMY`, while
the Saturn sound controller may require the M68K processor to run
during initialization. That is a hypothesis, **not proof** that
audio synchronization is causing black video.

## Exact one-variable comparison

`tools/patch_yabause_private_c68k_experiment.py` modifies the same
Stage102 pinned public source: **only** the original-game frame mode's
`source_game.m68kcoretype` becomes `M68KCORE_C68K`. Other dummy
and synthetic regression modes are unchanged. The independent public
C68K implementation is enabled via `-DYAB_WANT_C68K=ON` in CMake.

Public GitHub CI compiles the authentic pinned upstream GPL Yabause,
checks synthetic game-free scenarios and produces only its public
instrumented executable. No user's original BIN/CUE, game code,
scene images, CD callbacks or protected source data enter CI.

A private operator compares two clean 0700 process workspaces with
identical original media, exactly 600 emulated frames, frame-counter
checkpoints, CD FAD logs, VDP numerical state and the local-only
SH2 instruction snapshots. The two binaries should be independently
hash-pinned. Neither session may reuse an output file or share a gate.

## What would advance the hypothesis

If C68K changes the observed SH2 wait behavior, resource reads,
VDP layer/palette counts or RGB pixels, the sound co-processor
dependency becomes more plausible. If the traces are identical,
C68K alone is not the resolution. Even if a colored output is
rendered, the original game menu and first battle must still
be independently visually verified.

Issue #11 remains BLOCKED pending visible original game frames
and synchronized callback evidence. Never publish private opcode
windows from the original game.
