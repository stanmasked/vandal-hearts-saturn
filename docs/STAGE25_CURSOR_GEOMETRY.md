# Stage 25 — Shared cursor and screen-projection contract

Native ROM-free tactics prototype. Authentic Sega Saturn geometry and original first battle are **not** decoded.

## Motivation and fix

Before this stage, keyboard and controller directions duplicated cursor movement operations in `src/ui/sdl_main.cpp`, and the renderer kept its own isometric projection. A later change to one side could silently invalidate NeXium Stage 24 cursor-movement expectations.

Added header-only C++17 `include/vh/cursor_geometry.hpp` with `advance_cursor` (bounded four-direction movement) and `project_training_tile` (synthetic 1280×720 isometric coordinates, 40×20 pixel half diamonds, and elevation offset 18). Both SDL keyboard and controller handlers use the shared movement function; the renderer uses the shared projection. No SDL dependency is introduced into the reusable header.

Initial cursor at grid cell `(1,5)` projects to `(480,256)`. Right steps to `(2,5)` and projects to `(520,276)` — exactly **+40 horizontal / +20 vertical**. The optional X11 `Right` probe can compare against these known expectations, but cannot establish that NeXium actually delivered the key.

## Verification

Added `tests/cursor_geometry_tests.cpp`, enabled as `cursor_geometry_contract` CTest. An independent local ROM-free CMake C++17 build passed both `tactical_core` and `cursor_geometry_contract` (2/2). The new test executes 17 direct assertions: coordinates, directions, boundaries, elevation, and invalid map dimensions. The full GitHub branch additionally has the previous `startup_smoke_contract` and Python tests, which require separate CI validation.

README now correctly distinguishes independently verified native NRO compilation from **still-unverified NeXium display, runtime and input**. No original Saturn disc bytes/assets enter GitHub.
