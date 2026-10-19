# Stage 07 — MAP mirrored changes and candidate 64-element pitch

Source is the user's privately held Sega Saturn Vandal Hearts image, English v1.1 (translation-patched). The findings do not establish equivalence to the unmodified 1997 Japanese release.

## Confirmed measurements

Comparing **M_MAP13.MAP** and **M_MAP14.MAP**, each with 466 active candidate 12-byte records:

- Exactly **69** different second-word values in those records.
- Exactly **69** different 16-bit tail values beginning at file offset 0x24400.
- All 69 before/after value pairs are distinct **within each section** and have a **one-to-one matching partner** in the other section (matching multisets).
- The positions in the later table are not in the same order as the positions in the record table, ruling out a naive positional copy.
- Over candidate lags 16–96, **64** has the strongest recurrence among changed tail indices: **60** repeated pairs.
- If row pitch **64** is assumed, changed indices occupy a 9-by-9 bounding region, rows 4–12 and columns 4–12, with per-row changed counts **5, 7, 9, 9, 9, 9, 9, 7, 5** (69 total).

The 9-by-9 footprint and 64-word recurrence are evidence for possible spatial indexing. **They do not prove** a true map width, tile interpretation, level geometry or mission assignment. Alternative explanation (e.g. packed per-surface or graphical descriptors) has not been excluded.

## Tool and tests

Use `python3 -m tools.saturn_map_patch "/private/Track 1.bin" --output stage07.json`.
The report contains only numeric statistics and no source game bytes; the original disc is never published.

Six new synthetic unit tests validate word-pair matching, permutation resistance, pitch selection, expected row counts, malformed input, and rejection of altered mappings. All **35 Python unit tests** and **C++ CTest** passed locally. GitHub Actions results require separate CI confirmation.

## Next validation gate

Correlate the 64-pitch area with larger sample pairs, then examine candidates for geometry / event links against actual running Saturn output. No claim of a decoded first mission, real character sprites, or runnable Switch NRO is made.
