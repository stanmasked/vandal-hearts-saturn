# Stage117 — controlled third-C dialogue continuation

## Purpose

Stage115's private original-disc run reached the opening tactical map, but Magnus's “Ah... a hidden room.” line remained visible through frame 48,000. Stage116 adds a second C confirm at frame 31,200 to both cold boots and uses an enable bit to distinguish the paired runs. The next narrow experiment schedules a third C at frame 36,000 in both runs, with only the third-C enable bit changed.

This experiment tests whether that third input advances the dialogue. A framebuffer difference is only an integrity signal; it is not by itself proof of dialogue progression or player control.

## Runner contract

The Stage117 source transformer composes Stage116 on the pinned public Yabause source, then adds \`VH_SATURN_CONFIRM_AT_FRAME3\` and \`VH_SATURN_CONFIRM3_ENABLED\`. It preserves the 48,000-frame cap, native active-low C-bit checks, Stage101/102 video and SH2 diagnostics, and the inherited frame loop.

Both paired runs receive the same schedule:
- START press/release: frames 12,060–12,066.
- First C press/release: frames 12,240–12,246.
- Second C press/release: frames 31,200–31,206, enabled in both runs.
- Third C scheduled press/release: frames 36,000–36,006; enabled only for the intervention run.

The schedule and all environment entries other than \`VH_SATURN_CONFIRM3_ENABLED\` must be identical. The control still receives the frame-36,000 schedule, but does not press C.

## Acceptance gates

- Verify the original media and public runner fingerprints before and after both processes.
- Require exactly 400 valid 120-frame PNG checkpoints per process, plus canonical numeric video/SH2 logs and exact native pad receipts.
- Require byte-identical `pre.png` files and all checkpoints to match through frame 35,880 (299 checkpoints), including matching pre-START and pre-first-C ranges.
- Require the two private output directories to be siblings with equal-length absolute paths, so HOME/TMPDIR/capture-path values have matching shapes between processes.
- Require the first post-third-C divergence by frame 42,000, then privately inspect the relevant frames to determine whether the dialogue actually advanced.
- Keep \`first_battle_or_player_control_verified\` false unless the original tactical HUD/turn state and a response to player input are independently observed.

Public CI must use only synthetic media and may publish only the public GPL emulator executable. Original BIN/CUE, screenshots, raw CD traces, and frame hashes remain private.
