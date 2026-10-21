# Stage68 — neutral terrain-only bridge into native C++ (research)

The first battle is not decoded. This stage supplies a deliberately limited
bridge for **privately observed numeric geometry** only, based on the already
validated Stage66 and Stage67 evidence contracts.

## Workflow

1. Independently capture original Saturn gameplay; record provenance, source
   edition, grid cells, unit observations and action evidence in a private
   Stage66 manifest. Unknowns are explicitly null and prevent export.
2. Pass the Stage67 completeness gate. It does not authenticate the source.
3. Export the numeric `.vhterrain` format locally:

```bash
python3 -m tools.saturn_terrain_bridge /private/first-battle.json \
  --output /private/first-battle.vhterrain
```

4. `vh::load_unverified_terrain(std::istream&)` loads the generated text into
   a native `Battle` **with no units**. The format is strict row-major:
   `VH_TERRAIN_UNVERIFIED_V1`, `SIZE W H`, then one
   `CELL x y elevation cost walkable` per grid position.

## Hard exclusions

- No unit attack/defense/range or combat rules: these remain unverified and
  are **never filled with demo defaults**.
- No copyrighted graphics, audio, scripts, hashes, binary map values or disc
  images are exported.
- The format name explicitly marks all geometry as unverified, even with
  complete Stage67 coverage; no stage claims first-battle authenticity.
- Native parser refuses missing, duplicated/out-of-order, excessive, malformed
  or overflow-prone values; source coordinates must fit the 128x128 core.
- Generated files use the gitignored `.vhterrain` extension and must remain
  outside this public repository.

Host/GCC/Clang C++ and Python tests use a 2x2 fabricated map, never original
Saturn art or values. The Switch NRO code is not yet connected to a game scene
loader; a separate review will gate any future use in a real mission.
