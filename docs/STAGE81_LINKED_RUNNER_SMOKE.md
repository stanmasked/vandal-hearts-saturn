# Stage81 — link and launch the real Yabause runner without game media

## Scope

Stage80 successfully compiled the **core static library** under GCC and Clang.
Stage81 uses the existing upstream **runner frontend** from the same pinned
Yabause revision, compiles and links the actual executable against the
instrumented core, then invokes its **argument validation** with **no arguments**.

This is a genuine operating-system launch of a linked Yabause program,
but **not a Saturn boot, BIOS emulation, or simulated game execution**.
The expected output comes from the runner's own original `main`:
`Not enough command line arguments.`.

## Fixed public inputs

- Yabause upstream commit: `7e38821dbac265490f115e163c523a939acda759`.
- Yabause `cdbase.c` Git blob: `d56d5dd1941b553c0ede111a83fcf8e50dbecb45`.
- LodePNG upstream commit: `e584a8490db1b76b81bf298c11c09d3b55d9c270`.
- LodePNG `lodepng.cpp` blob: `4915ed7a1ddc827559eb42b8968924a61454f2e6`.
- LodePNG `lodepng.h` blob: `8f789b677668a495f641336cf62f3afe0b98a80d`.

The upstream historical runner's CMake skips the port when its
`lodepng` header and C++ file are unavailable. Stage81 restores those
public MIT/Zlib-licensed dependencies temporarily in the Actions
workspace, pinned to exact git objects. No dependency source is
checked into our game project. The original public Yabause source is
GPL-covered; its license must be respected for any redistribution of
an instrumented emulator.

## What the test proves

1. Two public repository revisions match their immutable commit IDs.
2. Their relevant blobs match pinned Git object IDs.
3. Our patch is applied to the complete upstream `cdbase.c`.
4. The Yabause library plus original runner frontend link.
5. The linked executable launches on the host and accepts an ordinary
   argument-checking path without mounting any disc.

## What it does **not** prove

- Yabause initializes Saturn SH2, CD hardware or a BIOS.
- An ISO/CD image of Vandal Hearts Saturn was loaded.
- A sector was read, or a real FAD record was captured.
- The Saturn battle scene, map, turn rules or source-version identity
  were authenticated.

Actual BIOS/game activation and timed read windows remain separate
private-only tasks under Issue #11.
