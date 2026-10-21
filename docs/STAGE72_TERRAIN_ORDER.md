# Stage72 — order-sensitive synthetic terrain identity

## Motivation
Stages69–71 verify that Python's exported terrain is accepted by C++ and
that aggregate width, height, elevation sum, movement-cost sum and count of
blocked cells match. But those sums cannot detect **permutations**: exchanging
the elevation or cost of two tiles can preserve every aggregate while changing
the pathfinding and rendering behavior of the map.

## Verified by this stage
- `vh::ordered_terrain_digest(Battle)` traverses the **actual parsed C++
  tiles** in row-major order, mixing grid dimensions followed by each
  signed elevation (LE32 modulo 2^32), movement cost (LE32) and walkability
  (one byte) using FNV-1a-64.
- Python independently derives an ordered digest from **generated tile
  dictionaries**, without trusting the native output or its input bytes.
- CI calls the compiled `vh_terrain_order_probe` on seven fully invented
  grid sizes from 2×2 through 128×128. The digests must match exactly.
- Four equal-sum permutations deliberately swap costs, elevations, whole
  payloads and walkability between locations. Native digests must differ
  from the baseline and match the independently recomputed Python digest.
- C++ host regression tests prove read-only behavior, each field's influence
  and dimension sensitivity. Neither the parser nor the digest creates units.

## Limits and confidentiality
This checksum is *not a cryptographic hash* or security protection, and its
agreement does **not authenticate Saturn source data**. GitHub CI uses only
fabricated 2D maps; no original screenshots, BIN/CUE, game scripts, map
geometry or character parameters are uploaded. The 1997 first battle remains
unverified until independent observation and source-resource correlation,
tracked in Issue #11.

Run on a host:
```bash
cmake -S . -B out && cmake --build out --parallel 2
ctest --test-dir out --output-on-failure
python3 -m tools.check_terrain_order --binary out/vh_terrain_order_probe
```
