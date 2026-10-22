# Stage112 — privately enter the first tactical battle

## Starting point
Stage110 has now been privately run with the verified original English-v1.1 Saturn disc. The no-input control remained on "Press START Button" at frame 13200; one START pulse at 12060–12066 changed the genuine title screen to the original menu (New Game / Continue / Settings) by frame 12120. The original media and Stage109 runner SHA-256 pins remained unchanged. No game screenshots, FAD logs or disc bytes were published.

## Dual-pulse runner
Stage112 builds the same pinned public Yabause commit and lodepng dependency as Stage109, with a small source transformation that:
- preserves the original six-frame START pulse and adds optional VH_SATURN_START_AT_FRAME2;
- rejects a second pulse without the first, a pulse closer than 12 frames to the first, or any pulse outside the bounded frame window;
- checks the same real Saturn active-low pad bit around each press/release and records only numeric private events;
- extends the maximum bounded capture to 24000 frames and keeps the 120-frame PNG checkpoint cadence (200 checkpoints at the full limit).

The new GCC/Clang workflow uses no original media and publishes only the GPL emulator executable. Original disc images and all runtime captures remain private.

## Private run
After the Stage112 GCC artifact from a successful Actions run is downloaded and its executable SHA-256 independently pinned, place the original Track1, Track2 and CUE in the same protected directory, preserving the exact basenames from the CUE. Create separate empty 0700 directories for control and new-game. Run each as an isolated process with the private allowlist environment, 24000 frames, and full Stage02 source hashes checked before/after. For the intervention set:
- VH_SATURN_START_AT_FRAME=12060
- VH_SATURN_START_AT_FRAME2=12240

The control run has neither variable. Confirm byte-identical pre-first-input frames (11880, 12000), then visually inspect frames around 12120 (menu), 12360, 13200, 18000 and 24000. Require all 200 checkpoint PNGs, both pad-state transitions, closed gate, correct frames.stats, and unchanged media/executable hashes. If the first battle has not loaded by frame 24000, inspect the private checkpoints and extend only after the next bounded-window review.

A menu image alone is not first-battle proof. Keep Issue #11 open until the actual original tactical map/battlefield and its loader/CD behavior are visually confirmed. Never attach original images, audio, BIN/CUE, FAD logs or extracted game resources to GitHub.
