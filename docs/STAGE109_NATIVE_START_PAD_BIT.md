# Stage109 — actual Yabause Saturn START padbit witness

## Source-established active-low bit

The exact historical public Yabause source fixed at commit
7e38821dbac265490f115e163c523a939acda759 includes
yabause/src/peripheral.c. Its genuine PerPadStartPressed implementation
clears bit 0x08 of the controller's first data byte:

    *pad->padbits &= 0xF7;

PerPadStartReleased restores that bit:

    *pad->padbits |= ~0xF7;

This is a checkable public-source property, not extracted game code or
a synthetic Saturn controller. On the real standard-pad memory, 0 means
START pressed and 1 means START released.

Stage107 already attaches a real standard pad to PORTDATA1 after the
emulator initializes. It issues a START pulse at frame 12060 and
releases on frame 12066, preserving exactly the same 13,200-frame
control/pressed A/B experiment.

## Stage109 improvement

The Stage109 public-source runner patch retains *all* Stage107
emulator operations, inserts only numerical readbacks of the
actual pad's first byte after registration, immediately after the
START press, and after START release, and rejects unexpected values.
The readbacks are adjacent to the Yabause pad API calls, immediately
before the respective YabauseEmulate step.

A separate new private-only file pad-state.txt contains:

Control:
    VH_PADSTATE initial_start_bit=1
    VH_PADSTATE mode=0 completed_frames=13200

Pressed:
    VH_PADSTATE initial_start_bit=1
    VH_PADSTATE frame=12060 start_bit=0
    VH_PADSTATE frame=12066 start_bit=1
    VH_PADSTATE mode=1 completed_frames=13200

The source output is produced in the existing protected capture
directory with the same private umask 077 as Stage107. Stage107's
pad-events.txt receipt is unchanged. No game pixels, disc bytes,
SH2 instructions, or original CD sector addresses are logged.

If a source-pinned run has created both sets of protected local
Stage107/Stage109 witnesses, verify them with:

    python3 -m tools.saturn_private_start_bit_ab --control /private/control --start /private/pressed

The validator reuses Stage107 strict permissions, pulse timing,
frame-13200 PNG integrity and numeric FAD log checks. It compares
each pad-state byte against the exact expected active-low sequence,
rejecting wrong frames, altered bits, missing entries and symlinks.
It prints only non-identifying yes/no metadata.

## Evidence boundary and next acceptance

A successful Stage109 pad-bit witness demonstrates that genuine Yabause
**host peripheral memory** changed in response to the API calls.
It does *not* independently demonstrate that Saturn guest software
queried SMPC input, recognized START, opened a menu or loaded combat.

To prove a genuine title-to-menu transition, run the same trusted,
full-SHA-pinned original English-v1.1 disc in separate protected
no-START and START sessions, compare identical pre-input
checkpoints (Stage108), inspect post-input graphics privately,
and cross-check numeric CD behavior. Actual gameplay and original
first battle still require independent evidence; Issue #11 remains open.

Stage109's public GCC/Clang workflow compiles pinned GPL Yabause and
runs synthetic/no-media verification only. It uploads just public
Yabause executable artifacts; the original game disk, private
screenshots and traces are never transferred to CI.
