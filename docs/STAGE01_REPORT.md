# Stage 01 verification log — 2026-10-20

## Verified in this environment
- GCC 14.2.0: `cmake` configure, build and `ctest` passed.
- Clang 17.0.0: `cmake` configure, build and `ctest` passed with
  `-fsanitize=address,undefined -fno-omit-frame-pointer`.
- Native CLI script: moved a test character and advanced one full test round,
  with enemy AI movement reflected on the displayed map.
- C++ tests: 6 test functions covering movement, terrain, cliffs, occupancy,
  battle actions, invalid input, damage/outcome and enemy phase.
- Python tests: 3 synthetic-only checks for CUE metadata parser.

## Not verified
- Nintendo Switch `devkitPro` SDK is not installed here: `.nro` not built.
- SDL2 headers/libraries are not installed: isometric UI not compiled or run.
- NeXium or Nintendo Switch hardware not tested.
- No original Sega Saturn disc image has been supplied or analyzed.
- No authentic Saturn battle rules, scenes or assets have yet been recreated.

## Next gate
Obtain a personally owned Saturn T-9526G disc dump locally and run the
read-only inventory; inspect the Saturn-specific first battle before replacing
test placeholders. Keep disc content and derived media private, out of git.
