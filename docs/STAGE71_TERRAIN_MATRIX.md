# Stage71 — signed elevation and synthetic terrain import matrix

## Objective
Stage69 proves one fabricated 2×2 Python-export → compiled C++ parsing
round-trip. Stage70 independently verifies C++ move calculations on an
invented imported map. Stage71 stress-checks the **interchange protocol**
across rectangular, narrow and native-maximum map dimensions, preserving
signed relative elevations without confusing coordinates with heights.

## Change in Stage66 evidence schema
Previously, the generic nonnegative integer validator was inadvertently
used for `cell.elevation`, even though Stage68 export and the native C++
parser already support signed heights. Stage71 accepts signed integer heights
(including negative relative elevation) but still rejects booleans and keeps
coordinates, HP, cost and movement budgets under their own restrictions.
Export continues to enforce the bounded range −100000..100000.

## Cross-language matrix
The host CI invokes the existing compiled `vh_terrain_probe` on seven
invented grids: 2×2, 3×5, 7×13, 17×9, 1×128, 128×1 and 128×128.
The importer must independently agree with the generator's tile counts,
walkability, movement-cost sum, elevation sum and zero units. Extra or
truncated records and oversized native dimensions are rejected; invalid
numeric ranges are rejected by the Python exporter.

## Status limits
- All evidence and units are **fabricated synthetic test records**; no
  original Saturn source is parsed and no copyrighted media are included.
- A complete synthetic evidence manifest does not authenticate source data.
- The current prototype uses its own invented movement-height rules.
- This does not create the first original Saturn mission. That milestone
  remains blocked by original-runtime observations and source correlation
  under [Issue #11](https://github.com/stanmasked/vandal-hearts-saturn/issues/11).

Run:
```bash
cmake -S . -B out
cmake --build out --parallel 2
python3 -m tools.check_terrain_matrix --binary out/vh_terrain_probe
```
