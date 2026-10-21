# Stage 08 — Candidate 64-word periodicity across all Saturn MAP files

This report summarizes **numeric statistics only** from the user-owned Sega Saturn
T-9526G English v1.1 translation-patched disc image. It does not include game
content, extracted assets, graphic data, original code or map tile values.

## Method

For each of 74 equal-length 170,624-byte MAP files:

1. Read BE16 words from candidate tail region [0x24400, 0x29A80).
2. Record indexes of words that are not zero **in private memory only**.
3. For each lag from **16 through 96** count how many occupied indexes also
   have an occupied index that lag later.
4. Sort candidate lags by **descending count, then ascending lag**. Rank lag
   **64** under this deterministic definition. Report numeric rankings only.

This is a **positional occupancy autocorrelation**. Repetitive structures
unrelated to in-game geometry can also produce a peak at 64. It is not
confirmation of a physical grid width.

## Measurements (all 74 maps)

- Lag **64** is the highest-scoring candidate in **51** maps.
- Lag **64** appears in the top 4 scoring lags in **70** maps.

| Family | Maps | 64 highest | 64 in top four |
| --- | ---: | ---: | ---: |
| M_MAP | 34 | 19 | 33 |
| M_IVE | 22 | 21 | 21 |
| M_KEY | 17 | 10 | 15 |
| M_SHOW | 1 | 1 | 1 |
| **Total** | **74** | **51** | **70** |

Four exceptions where lag 64 is not among the four highest-scoring:
`M_MAP23.MAP`, `M_IVE22.MAP`, `M_KEY06.MAP`, `M_KEY12.MAP`.

## Reproduction

```bash
python3 -m tools.saturn_map_tail_pitch "/private/Track 1.bin" \
  --output "/private/stage08_tail_pitch.json"
python3 -m unittest discover -s tests -p "test_*.py" -v
ctest --test-dir out --output-on-failure
```

The module produces JSON counts, ranks, candidate lags, source file **names**,
but never original word values, bytes, graphics or executable data.
Eight additional synthetic tests were introduced in this stage, bringing the
local Python unit-test suite to **43 tests**, all passed, and C++ CTest passed.

## Next research gate

Identify which section actually controls scene geometry by comparing map
variants and captured Saturn in-game behavior. Confirm the grid origin and
orientation, and reject alternative explanations for lag-64 autocorrelation,
before writing a map importer. Native Switch NRO/NeXium remains unverified.
