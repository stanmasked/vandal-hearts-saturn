# Vandal Hearts — Sega Saturn → Nintendo Switch (native remake)

**Stage 01 / ROM-free prototype.** Separate from the PlayStation-based remaster.
The intended reference is the 1997 Japanese Sega Saturn edition `T-9526G`.

> Status: C++17 tactical-core prototype and synthetic 8×8 map, NOT the real game,
> NOT an authenticated Saturn mechanics recreation and NOT a confirmed NRO.

## Current capabilities

- Platform-independent C++17 tactical simulation: tiles, terrain movement costs,
  elevations/cliffs, occupancy, pathfinding, attacks, health, turn phases.
- Deterministic test-only damage and placeholder enemy AI.
- Host interactive CLI and optional SDL2 isometric visualization.
- Switch homebrew `.nro` recipe using devkitPro/libnx + SDL2, awaiting target build.
- Disc CUE/BIN metadata-only hash inventory (read-only, strictly local).
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

## Nintendo Switch homebrew build (not tested in this workspace)

Install `switch-dev` and `switch-sdl2` using devkitPro `dkp-pacman`, configure
`DEVKITPRO`, and ensure `sdl2-config` points to Switch portlibs, not host SDL2.

```bash
make
# intended output: vh_saturn_demo.nro
```

The Makefile follows the standard `switchbrew/switch-examples` SDL2 template.
Switch compilation and NeXium/real console runtime **still require validation**.

## Original-disc material and repository policy

This source repository must never include original Saturn BIN/CUE/CHD/ISO, music,
art, scripts, extracted content or third-party translation patches. The first
battle will be implemented from lawfully acquired privately inspected Saturn
assets in later stages. `private/` is gitignored and never uploaded.

See `docs/PLAN.md` for implementation milestones and `docs/RESEARCH.md` for
Saturn asset inventory protocol.
