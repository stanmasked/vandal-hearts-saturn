# Stage63 — authoritative read-only movement preview (ROM-free)

Base: Stage62 `2534506eb2dcabc531f6ac352191524c68ebae9d`, verified
GCC 20/20 + Python 447/447, Clang 20/20 + Python 447/447,
Switch NRO and real NeXium [#39619136162](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39619136162).

## Change
- Expose `Battle::preview_move(id, destination)` with `legal`, `path_cost`,
  `remaining_points`. All invalid requests are zero-valued.
- Actual `Battle::move` delegates to the exact same legality projection.
- Saturate path-cost accumulation below a dedicated infinity sentinel.
  Reject disconnected destinations even if an otherwise-valid unit was
  authored with `move_points=INT_MAX`. Enemy synthetic movement cannot
  mistake that sentinel for a walkable route.
- Read-only callers never mutate HP, movement flags, position, round,
  phase or the battle fingerprint.
- Added native C++ tests for costly terrain, ordinary terrain, Guard/Scout,
  blocked routes, occupied cells, cliffs, end states, spent movement and
  adversarial huge movement allowances / terrain costs.

## Acceptance
1. Host GCC and Clang CTest suites (new `movement_preview_contract`).
2. Existing Python screenshot/parser regression suite.
3. Nintendo Switch NRO build and all existing actual NeXium guest screenshot
   and lifecycle checks to catch gameplay/visual/fingerprint regressions.
4. Confirm existing Stage44/52/54–62 golden tactical hashes are unchanged.
5. Do not call Stage63 ALL GREEN before these checks pass.

This stage does not add a gameplay screen or claim to reproduce original
1997 Saturn pathfinding. The next step is to expose a player-visible hover
cost only after the invariant and regression checks are green. Actual Saturn
map/height/terrain data remain a separate private reference requirement.
