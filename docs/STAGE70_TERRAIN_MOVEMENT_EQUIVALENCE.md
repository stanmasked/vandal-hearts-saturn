# Stage70 — native tactics behavior on imported neutral geometry

## Scope
The Stage68 parser already turns a numeric-only `VH_TERRAIN_UNVERIFIED_V1`
file into a C++ `Battle` without units. Stage69 checks that Python's
independent exporter and the compiled C++ parser agree on tile aggregates.

Stage70 checks a different failure class: a grid can import correctly but
still give the *wrong tactical behavior*. To catch that, its native C++ test
compares a loaded invented 3×3 terrain map against a separately authored
reference `Battle` using direct tile assignments.

## Scenarios
- An expensive direct tile forces a cheaper four-step detour.
- A lower terrain cost makes the direct two-step route legal.
- A height cliff blocks the upper route and an enemy occupies the lower route.
- A non-traversable central tile forces the upper detour.
- Insufficient movement points hide an otherwise valid longer route.
- A missing/out-of-order terrain record is rejected before any battle is
  returned to its caller.
- All legal-destination preview costs and remaining points, reachable-tile
  overlays, tactical fingerprints and committed movement agree across
  imported/manual grids; read-only previews do not mutate the battle.

## Deliberate exclusions
All maps and units are invented only for tests. The bridge itself imports
**no units**; synthetic combat stats are supplied explicitly by the tests.
The comparison verifies *current prototype tactics* and does not claim
the 1997 Saturn game's pathfinding, classes, height rules or first-battle
layout have been independently recovered.

Stage70 adds the CTest `imported_terrain_movement_equivalence` to GCC/Clang
regression. No ROM, original art, audio, script or extracted geometry is
committed. Existing Switch NRO and real NeXium smoke remain required CI gates.
