# Stage 06: Candidate MAP record table and cross-region reference correlation

Source: user's privately supplied *English v1.1* translated Sega Saturn disc (`T-9526G`), not an authenticated unpatched Japanese master. This is a numerical research report, not an exporter or a fully decoded game format.

## Validated layout observations

- Every one of 74 files is exactly 170,624 bytes long.
- The area `[0x1E800, 0x23804)` is exactly 20,484 bytes, i.e. **1,707 slots of 12 bytes**.
- Treating each slot as six big-endian 16-bit words gives a continuous run of nonzero records followed by all-zero slots in **all 74** maps.
- **49,827** active records in aggregate; smallest file has **39**, largest has **1,707** (full table).
- Record fields at positions 0 and 2 have one of two consistent combinations across maps:
  - `(0x0046, 0x0088)` in **42** files;
  - `(0x0146, 0x00C0)` in **32** files.
- Within an individual file, fields **0, 2, 3 and 5** are constant across its active records. Field 1 varies; field 4 may vary in some files. Numeric values are **not assigned gameplay meaning**.

## Controlled pair: M_MAP13.MAP vs M_MAP14.MAP

Both files contain **466** candidate active records. There are **174** changed bytes (all at odd absolute offsets); these occur in exactly three groups:

- 69 changed second fields (zero-based word index 1) in the candidate 12-byte record table;
- 36 changed fifth fields (zero-based word index 4) in that same table;
- 69 changed 16-bit words in a separate candidate value table starting at `0x24400`.

Crucially, the multisets of **all 69 individual before/after value-pairs** from the second fields and those from the later table are *identical*. This suggests two related data structures or a mirrored index, but is **not** proof that either is a map-cell reference, art pointer, height or texture index. No source values are exported to GitHub.

## How to reproduce privately

```bash
python3 -m tools.saturn_map_records "/private/track1.bin" --output /tmp/saturn_stage06_records.json
python3 -m unittest discover -s tests -p 'test_*.py' -v
ctest --test-dir out --output-on-failure
```

`tools/saturn_map_records.py` outputs numeric counts, word positions and boolean correlations only. Its synthetic tests do not use any original-game media. Public GitHub actions never access the original disc.

## Next validation gate

1. Correlate candidate record indices with other map sections and related `.BIN`/`.DAT` files **locally**.
2. Verify geometry and objects using an independent Saturn runtime reference.
3. Only then introduce an authenticated gameplay map parser and local-only asset converter. Nintendo Switch `.nro` and NeXium testing remain unverified.
