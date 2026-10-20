# Stage 09 — candidate Saturn MAP multi-array occupancy

Source: user-owned English v1.1 translation-patched Saturn disc (T-9526G).
Only aggregate statistics and synthetic tests are published. No original assets.

## Hypothetical 64-word row segmentation

Tail [0x24400,0x29A80): 11,072 16-bit words = 173 rows of 64.
Proposed windows: A=28 rows, B=28, C=14, D=28, E=75.

## Validated survey of all 74 .MAP files

- A/B zero/nonzero occupancy masks exactly equal in **67/74** files.
  Exceptions: M_IVE22, M_KEY08, M_KEY15, M_MAP10, M_MAP18,
  M_MAP29, M_MAP31.
- A/B mismatches total **89** of 74 x (28 x 64) positions.
- A/B have **21,610** aligned nonzero positions and **zero identical**
  nonzero 16-bit values at these positions.
- Family A/B exact masks: M_MAP 30/34, M_IVE 21/22,
  M_KEY 15/17, M_SHOW 1/1.
- B/D exact in **2/74** files, with **76** occupancy mismatches
  and **21,624** aligned nonzero values, again zero identical values.
- A/D exact in **1/74** files with 165 occupancy mismatches,
  21,535 aligned nonzero values and 31 identical values.

### Interpretation

Shared occupancy structure and distinct values may reflect linked arrays
or per-position attributes. They **do not** establish authentic geometry,
heights, texture IDs, movement costs or collision. Boundaries are hypotheses.

Run locally (never upload original disc):

```bash
python3 -m tools.saturn_map_layers /private/track1.bin --output /private/stage09.json
python3 -m unittest discover -s tests -p 'test_*.py' -v
ctest --test-dir out --output-on-failure
```

Added 8 fully synthetic Python tests; **51/51** pass locally;
C++ CTest **1/1** passes. Switch NRO and NeXium still unverified.
