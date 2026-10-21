# Stage 21 — Protect the NeXium frame gate from false positives

## Problem

The Stage 20 screenshot verifier counted all blue and red pixels. The synthetic SDL application draws blue/red bottom-of-screen *legend squares* even if units are missing. Counting those squares is not proof that the tactics scene rendered.

## Fix

- Add a separate Pillow-based color-component analyzer tools/nexium_frame_verify.py.
- Analyze only 6% to 78% of image height, excluding the legend.
- Require at least two significant disconnected blue areas and two disconnected red areas, with blue bodies to the left of red bodies.
- Save a numeric-only verification result as runtime-evidence/frame-check.json.
- Ensure the run-in-nexium job performs actions/checkout@v4 so this module is available before inspection.
- Preserve existing image and emulator log artifact publication even on runtime failure.

## Tests and limitations

Seven synthetic PNG-scene test cases passed locally: expected scene, legend-only, one-blue/one-red, swapped sides, blank image, too-small dimensions and excluded legend colors. No original Sega Saturn assets used.

This is a conservative *visual heuristic* for the ROM-free 8×8 training scene, not an emulator correctness proof. Rendering can be visually wrong despite satisfying this signature; manual screenshot inspection and a separate live control probe are still required.

The Stage 20 NeXium workflow was queued when this change was prepared; no claim of an actual emulator startup or verified screenshot is made.
