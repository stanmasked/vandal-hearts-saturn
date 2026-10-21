# Vandal Hearts — Sega Saturn → Nintendo Switch (native remake)

**Stage72 verified; Stage73 private Saturn read-trace crosswalk in progress / ROM-free native prototype.**
Separate from the PlayStation-based remaster.
The intended reference is the 1997 Japanese Sega Saturn edition `T-9526G`.

> Status: C++17 tactical-core prototype and synthetic 8×8 map, NOT the real game,
> NOT an authenticated Saturn mechanics recreation. A real Switch `.nro`
> and synthetic-game NeXium guest runtime were verified in CI; physical Switch
> hardware and authentic Saturn campaign data remain unverified.

## Current capabilities

- Platform-independent C++17 tactical simulation: tiles, terrain movement costs,
  elevations/cliffs, occupancy, pathfinding, attacks, health, turn phases.
- Deterministic test-only damage and placeholder enemy AI.
- Host interactive CLI and optional SDL2 isometric visualization.
- Real Switch `.nro` compiled using devkitPro/libnx and independently hash-verified.
- Shared SDL-free cursor geometry and directional movement now under host tests.
- Temporary ROM-free pixel-encoded state checksum verifies guest tactical state
  in emulator screenshots, even when guest stderr is unavailable.
- Host/guest-verified movement, combat, Victory/Defeat, damage forecasts, HUD
  stats, turn indicator and movement allowance. Stage63's shared legal-move
  projection and overflow guards passed CI; Stage64's hovered cost/remaining
  HUD passed GCC/Clang, Switch NRO and real NeXium pixel checks.
- Disc CUE/BIN metadata-only hash inventory (read-only, strictly local).
- Stages65–67 validate source metadata and observation coverage; Stages68–71 verify geometry import and movement on fabricated maps up to 128×128 (Stage71: GCC/Clang 24/24 CTest and 509/509 Python tests, NRO and NeXium green). Stage72 checks *ordered per-cell* geometry (GCC/Clang 25/25 CTest and 514/514 Python, Switch NRO and NeXium verified). Stage73 adds a metadata-only first-battle-versus-menu read crosswalk and explicit Saturn FAD→ISO LBA normalization. Stage74 passed 25/25 CTest and 548/548 Python on both host compilers plus Switch NRO/NeXium. Stage75 passed private capture metadata preflight (GCC/Clang 25/25 CTest and 564/564 Python per compiler, Switch NRO and NeXium green). Stage76 verified the local FAD hook and log adapter on synthetic input (GCC/Clang 25/25 CTest, 575/575 Python per compiler; Switch NRO and NeXium passed). Stage77 adds a separate manually gated Yabause hook so numerical reads can be restricted to an operator-selected window (CI pending; original game not booted here). None of this authenticates original Saturn gameplay.
- Host GCC/Clang test workflow, no ROM or game assets in CI.

## Build and test on host (no SDL2 required)

```bash
cmake -S . -B out -DCMAKE_BUILD_TYPE=Debug
cmake --build out -j2
ctest --test-dir out --output-on-failure
./out/vh_cli
```

If SDL2 is installed, CMake additionally builds `./out/vh_sdl`.

## Controller demo commands (SDL2)

- D-pad / arrows or WASD: move cursor
- A / Enter: select friendly unit, or move selected unit to highlighted tile
- Y: attack enemy under cursor
- X: end the player turn and run test enemy AI
- B: cancel selection
- Start / Escape: exit prototype

The window title reports status. In-game Japanese/Russian/English text and fonts
are future tasks. This demo uses primitive shapes rather than original artwork.

## Nintendo Switch homebrew build (verified by GitHub Actions)

Install `switch-dev` and `switch-sdl2` using devkitPro `dkp-pacman`, configure
`DEVKITPRO`, and ensure `sdl2-config` points to Switch portlibs, not host SDL2.

```bash
make
# intended output: vh_saturn_demo.nro
```

The Makefile follows the standard `switchbrew/switch-examples` SDL2 template.
Switch cross-compilation and real NRO0/SHA-256 checks passed GitHub Actions.
CI has validated NeXium guest runtime on the ROM-free training scene.
**Physical Switch hardware remains untested.**

## Original-disc material and repository policy

This source repository must never include original Saturn BIN/CUE/CHD/ISO, music,
art, scripts, extracted content or third-party translation patches. The first
battle will be implemented from lawfully acquired privately inspected Saturn
assets in later stages. `private/` is gitignored and never uploaded.

See `docs/PLAN.md` for implementation milestones and `docs/RESEARCH.md` for
Saturn asset inventory protocol.
