# Stage 19 — Boot and first-frame diagnostic receipts

## Purpose

The Nintendo Switch ROM-free tactical prototype can now produce explicit
startup markers that tell a later emulator/console tester how far execution got.
These are **observations from actual code paths** and not automatically
fabricated test results.

## Runtime markers

The SDL2 application emits to standard error:

- `VH_SMOKE sdl=ready renderer=ready`: window and renderer created
- `VH_SMOKE scene=ready width=8 height=8 units=4`: synthetic training scene checked
- `VH_SMOKE first_frame=rendered`: a call to the SDL renderer finished
- `VH_SMOKE completed_frames=N round=R phase=P`: opt-in fixed-frame run finished

If SDL initialization or a renderer fails, the pre-existing SDL error paths
return nonzero instead of emitting a false success marker.

The optional argument `--smoke-frames=N`, for **1–600** frames, exits after
N rendered frames, and returns nonzero on malformed or duplicate settings.
When the argument is omitted, normal interactive controls and runtime remain
unchanged. Console/emulator argument passing may not be supported by every
launcher; startup and first-frame markers do not require any argument.

The "first_frame=rendered" marker means SDL_RenderPresent was **called**;
it does not prove that pixels were correctly displayed or seen by a user.
A verified NeXium video/screenshot test is still necessary.

## Test coverage

- Header-only smoke argument parsing and initial ROM-free training scene
  checks in `include/vh/smoke.hpp`.
- CTest target `vh_smoke_tests` with valid/invalid switches, scene invariants,
  and limit boundaries.
- Existing `tactical_core` CTest retained; the local host build passed
  **2/2 CTest targets**.
- SDL2 is unavailable in the current local host environment, so the revised
  UI source's cross-compilation must be verified by GitHub Actions using
  devkitPro/libnx and Switch SDL2.

These changes contain no original Saturn game resources. They do **not**
represent an authenticated first battle, or a confirmed NeXium runtime.

## Next gate

Confirm the independent NRO build action uploads the binary, verify its
actual header and SHA-256, then run it in NeXium and inspect startup markers
and the image frame. Do not interpret successful cross-compilation as an
emulator test.
