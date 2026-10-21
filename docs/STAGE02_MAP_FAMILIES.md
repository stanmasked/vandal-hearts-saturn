# Stage 02 — map-file family survey

A metadata-only cross-check of the user-owned English v1.1 Saturn RAW MODE1/2352 disc:

- All **74** files with the `.MAP` extension are exactly **170,624 bytes** long.
- Family `M_MAP01.MAP`–`M_MAP34.MAP`: **34** entries.
- Family `M_IVE01.MAP`–`M_IVE22.MAP`: **22** entries.
- Family `M_KEY01.MAP`–`M_KEY17.MAP`: **17** entries.
- `M_SH.MAP`: **1** entry.
- Other resources have candidate names `MAP_1_1C.BIN` and `MAP_1_1P.BIN` (84,480 and 512 bytes); the matching suffixes could indicate graphics/palette pairs, but this is not yet verified.
- `EVENTxx.DAT` and `EVxx.PRG` are present, but the precise script / event relationship remains unknown.

## Hypotheses, NOT yet established game behavior

The fixed 170,624-byte length suggests a stable shared record/container layout. The four map naming groups suggest different uses of map files. Neither the map dimensions nor the tile/height data can be inferred safely from names alone.

## Next required experiments

1. Compare byte offset distribution across the 74 files; detect invariant header fields, repeated blocks, and likely tile encoding.
2. Inspect linked `MAP_...C.BIN` / `MAP_...P.BIN` resources in private memory and test tentative graphics formats.
3. Cross-check discovered behavior against a running Saturn reference before attributing map IDs to actual missions.
4. Build a validated **neutral** map schema and synthetic fixtures first; only then add a local importer.

No original-game file bodies, screenshots, scripts, or executable code have been committed.
