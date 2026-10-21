# Stage 31 — Deterministic ROM-free tactical action replay

## Purpose

The Nintendo Switch ROM-free training demo now has a reproducible, numeric-only state fingerprint. This allows future debugging of inconsistent game-state updates across host GCC/Clang and native Switch builds. It does **not** claim authenticity to Sega Saturn Vandal Hearts tactics or the original first battle.

## Canonical serialization

Header-only `include/vh/replay.hpp` implements FNV-1a 64 over an explicitly defined stream: ASCII marker VHS1; little-endian 32-bit width, height, round and phase; 8x8 tile elevation, movement cost and walkability in row order; then units ordered by numeric unit ID, each with UTF-8 length-prefixed name, side, position, HP, combat stats, range and moved/acted flags.

No raw struct bytes, padding, host endianness, native pointers, original game assets or unstable unordered collections enter the checksum. Note that FNV-1a is a regression checksum, **not a cryptographic integrity/security guarantee**.

## Fixed five-command replay

1. Attempt out-of-range Scout→Archer attack: rejected, state unchanged.
2. Move Scout from (1,5) to (2,5), entering a cost-2 tile: accepted.
3. Attempt another Scout move in same round: rejected, state unchanged.
4. End player turn: accepted; ROM-free placeholder enemy AI resolves, round advances to 2.
5. Move Guard from (1,6) to (2,6): accepted.

Initial fingerprint **ae38b0b5ab887f00**; final fingerprint **2f913924d3742298**. Other intermediate hashes emitted by `vh_replay_cli` are numeric state receipts. The fixture is written from scratch, not extracted from Saturn.

## Added and changed

- `tests/replay_tests.cpp` validates accepted/rejected actions, non-mutating invalid commands, fresh-instance determinism, round progression, terrain perturbation, unit-name sensitivity and insertion-order-independent canonicalization.
- `src/app/replay_main.cpp` produces a six-line `VHS_REPLAY` transcript with the initial hash and five result checksums. Build using CMake and run `./out/vh_replay_cli`.
- `src/ui/sdl_main.cpp` emits `VH_STATE` during ROM-free scene initialization and after any actual accepted state-changing SDL input. It also emits `VH_CURSOR x=... y=...` when the cursor moves. These are **guest-side calls**; NeXium may or may not forward guest stderr to the host log. No receipt is synthesized unless the corresponding code path executes.
- CMake registers the host CTest target `deterministic_replay_contract`; the real Switch Makefile builds the SDL runtime and can include the header directly.

## Independently executed checks

Local GCC and Clang C++17 builds passed the replay CTest and produced identical initial/final fingerprints. Exact golden fingerprints are asserted in the test; changing the combat core in a way that affects the replay will fail instead of silently altering expected outcomes.

## Limitations / next gate

CI must run on the new Stage31 head for cross-compiler verification; actual NeXium host output/inputs still need separate evidence. A screenshot already confirmed ROM-free frame rendering on an earlier build, but steady-state X11 runtime remains unresolved. The authentic first Sega Saturn mission's data and graphics are not decoded, and no copyrighted game assets are published.

