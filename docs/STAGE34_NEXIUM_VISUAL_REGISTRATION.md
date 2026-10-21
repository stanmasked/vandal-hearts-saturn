# Stage 34 — Relocate guest state marker and calibrate real NeXium screenshots

## Evidence from real NeXium artifact

Run #39404961076 (Stage29) generated real `nexium-window.png` and `nexium-after-right.png` with an Xvfb Openbox session. Both are 1279×700 window screenshots (NOT 1280×720). The yellow isometric selection moved approximately +34 pixels X and +15 pixels Y after X11 Right; the source game-board region visibly changes. The optional visual cursor check reported `plausible_right_cursor_movement=true`, and the input-probe receipt confirms a second screenshot was taken. This is strong evidence of keyboard-to-guest cursor response in the ROM-free demo, but no proof of Nintendo Switch physical controller operation.

The frame shows NeXium's performance HUD in the upper-left, obscuring the entire Stage32 debug matrix that was previously at logical x=20..112, y=20..112. Even if Stage32 had compiled and run, its exact-1280x720 screenshot assumption and HUD obstruction would force a false negative. Stage33 host bridge also still mutated the *old* pixel `(24,24)` and would become a false negative when the matrix moved.

## Runtime failure isolated to closing the NeXium GUI

The same Stage29 run successfully captured both images, then `windowclose_sent` was recorded. `nexium-log-before-close.log` contains only ALSA missing-device warnings. `nexium.log` includes a Rust winit-0.30.13 panic at `window.rs:1200`, caused by X11 `BadWindow/TranslateCoordinates` against the closed X11 window. NeXium exited with status **101**. The phase-audit reports `fatal_before_close=[]`, `fatal_after_close_request=['rust_panic']`; stable guest startup/cursor response are distinct from the known broken host close path. No stability success is claimed.

## Fix in this stage

1. Moved the synthetic guest-rendered 64-bit debug grid to the unused upper-right area: cell origin (1050,38), 8×8 cells, 14px pitch, 10px size. Registration squares are now at logical (1028,16), (1180,16), (1028,168), away from NeXium's left HUD.
2. Replaced strict raw coordinate sampling in `tools/nexium_visual_digest.py` with identification of three magenta square components, validation of their 152-pixel right-angle geometry, then independent X/Y scaling and translation computed from their centers. The 64 bit samples are taken at calibrated cell centers.
3. Real window shape 1279×700, scaled/letterboxed synthetic windows and 1280×720 host images all pass the same strict bit-by-bit checksum check. No anchors, one wrong bit, corrupted cell, extra magenta component or malformed dimensions/reference must fail.
4. Updated C++ spatial-contract assertions and cross-language test's corruption pixel to the shared moved marker coordinates. The C++ fixture and Switch renderer both obtain cell/anchor rectangles from the same `include/vh/visual_digest.hpp`.

## Local test results

- **13/13** synthetic Python registration tests passed, including real observed NeXium window size and simulated HUD overlay.
- GCC and Clang independently passed updated C++ marker geometry tests and the C++→PPM→Pillow bridge; initial ROM-free checksum `ae38b0b5ab887f00`, moved checksum `ef9c7d67953c9b2a`.
- Real older Stage29 screenshot is correctly rejected because it predates the marker; no visual checksum claim is made for this actual historical run.

## Remaining validation

Stage34 CI must compile its own devkitPro NRO, run actual NeXium and decode its new top-right marker. Host winit shutdown panic remains an external emulator/GUI-lifecycle fault; do not downgrade fatal-log checks to mask it. The Saturn original first battle and real character/graphics/maps are not implemented and never published.

