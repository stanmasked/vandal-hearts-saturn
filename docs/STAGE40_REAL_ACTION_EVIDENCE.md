# Stage 40 — Actual NeXium keyboard battle action from screen-state evidence

## Prerequisites

Stage38 completed 3 independent real NeXium launch/cursor/close runs. Stage39 refactored SDL keyboard and gamepad bindings to share one ROM-free action contract. This stage now tests **real tactical movement**, not just UI cursor navigation.

## New opt-in real action trace

On the primary NeXium session only (`NEXIUM_ACTION_PROBE=1`), after its usual screenshot-verified Right cursor test, the launcher runs `tools/nexium_tactical_action.py` with the same live X11 window. It first checks both earlier real screenshots contain the unchanged initial battle checksum `ae38b0b5ab887f00`.

Because a previously dispatched Right can move 1 or 2 tiles, the script returns the cursor to the original Scout tile by individually issuing at most four bounded `Left` presses and checking the actual yellow component coordinates after each captured frame. It cannot assume a fixed number of Lefts. Then it issues `Return` to select Scout (selection leaves the battle checksum unchanged), `Right` to aim exactly one isometric tile (one verified retry permitted if the first press is entirely missed), and `Return` to commit the move.

**Authoritative acceptance:** the *actual guest screenshot* must encode the exact post-move full battle-state fingerprint `ef9c7d67953c9b2a`, known independently from the Stage33 host C++ tactical fixture. Merely sending X11 events, or moving only a yellow cursor, cannot satisfy it. It also requires an original initial checksum, correct return and precise one-tile aim.

Individual action PNGs and a structured `runtime-evidence/action-evidence.json` (or explicit failure) survive CI errors. The launcher still preserves graceful WM_DELETE/EWMH shutdown and independently captures the pre-close host log, never bypassing the Rust panic/lifecycle gates.

## Tests and CI

New `tests/test_nexium_tactical_action.py` uses production pixel-decoding and yellow-component analyzers on synthetic RGB scenes to verify successful exact move; returning from a two-tile initial Right; an aim retry after a missed event; rejection of a two-tile overshoot, unchanged battle hash, wrong initial screenshot, and missing proof files.

GitHub Switch NeXium job enables the trace **only in its initial session**, then separately runs `python3 -m tools.nexium_tactical_action --verify-dir runtime-evidence` with `if: always()`. Repeat-trials 2 and 3 remain unchanged and continue testing the existing cursor-input and clean-lifecycle contract, so regression reliability is not conflated with the new action probe.

This is still a ROM-free synthetic battle on a devkitPro homebrew Switch target through X11/NeXium. It is not proof of physical Joy-Con/Pro Controller button delivery or authentic Sega Saturn first battle fidelity. No original BIN/CUE/art/map/audio files are published.

