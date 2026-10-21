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
5. All acceptance gates passed on commit
   `7ff19a909fc4418101ab61b29e3c97dbfea69ccb`: GCC and Clang each 21/21
   CTest plus 447/447 Python tests; both Switch NROs built; NeXium guest
   workflow passed. See [Host CI #39623221976](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39623221976)
   and [NRO/NeXium #39623222294](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39623222294).

This stage does not add a gameplay screen or claim to reproduce original
1997 Saturn pathfinding. Stage64 adds a player-visible hovered cost cue with independent NeXium
pixel auditing; see `docs/STAGE64_MOVEMENT_PREVIEW_HUD.md`. Actual Saturn
map/height/terrain data remain a separate private reference requirement.
