# Stage108 — pre-input reproducibility gate for original Saturn START A/B

## Why this is necessary

Stage106 privately observed the genuine English-v1.1 Saturn title at 12,000
emulated frames. Stage107 added a real first-port Saturn pad, a no-input
control, and a six-frame START pulse on emulated frames 12060–12065 (release
at frame 12066), both running for 13,200 frames.

Merely seeing different final PNGs or different CD logs does NOT show that
the game accepted START. Differences can also arise from unrelated
nondeterminism. Before comparing post-START behavior, verify that the two
independently captured sessions are reproducible *before* the pulse.

## Private Stage108 extension

The new private-only Python auditor
tools/saturn_private_start_baseline.py first invokes the Stage107 A/B
evidence-integrity validator, enforcing:

- two different protected private capture directories;
- canonical numeric-only FAD logs (never raw source sector contents);
- the exact local controller receipt: START PRESS frame 12060,
  RELEASE frame 12066; the no-START control has no button events;
- both sessions claim 13,200 completed emulator frames.

It then validates the real PNG structure and CRC for checkpoints
**11880, 12000, 12120 and 13200** in *each* run. They exist because
the pinned Yabause runner writes checkpoints every 120 completed frames.

Both pre-input PNG files at **11880** and **12000** must be byte-identical
between the two runs. The same-frame dimensions must match at all four
checkpoints. If pre-input files differ, STOP: no conclusion about causal
response to START can be drawn from the two subsequent post-input files.

The auditor then reports only whether the post-input files at **12120**
and **13200** differ. It intentionally allows both outcomes. No pixels,
file hashes, paths, source disc data, original movie content, or numeric
FAD addresses are printed by the auditor.

## Run privately after a Stage107 verified A/B capture

Use two distinct directories with private permission 0700 and files 0600,
as in Stage107. The same source-pinned executable and unchanged
Stage02-matched Track1, Track2, CUE must be used for both original game runs.

Then run, in the protected workspace:

    python3 -m tools.saturn_private_start_baseline --control /private/control --start /private/pressed

Only the metadata-only printed JSON may be copied into a development
report. Do NOT post original screenshots, private media, raw FAD logs
or game instruction words to public GitHub.

## Evidence boundary

A passing Stage108 report confirms only reproducible file-level pre-input
screenshots, as far as the protected files demonstrate. It does not
independently attest the true emulator frame counter, controller hardware
sampling, menu text or guest code reaction. Full FAD logs are not frame
aligned by this analyzer.

The actual title-to-menu transition must still be visually confirmed in
private, and any genuine first tactical battle must additionally have its
battlefield, map loader and gameplay evidence verified. Issue #11 remains
OPEN. This stage's public CI uses ONLY invented 64x64 PNGs and invented
numeric FAD lines, never game media.
