# Stage 04 — structural survey of Saturn .MAP files

Source: user-owned **English v1.1 translated** Saturn disc, product ID `T-9526G`.
This report is metadata-only. No original media, source file content, textures or audio
was sent to GitHub.

## Verified numeric observations

- 74 files with `.MAP` extension, each **170,624 bytes**.
- Groups: **34 `M_MAP`**, **22 `M_IVE`**, **17 `M_KEY`**, **1 `M_SHOW.MAP`**.
  (Correction: previous note said `M_SH`, but actual filename is `M_SHOW.MAP`.)
- Byte order in initial inspected numeric fields is represented as **big-endian**;
  field meanings have **not** been identified.
- Third and fourth 16-bit words match in **22** files.
- Fifth 16-bit word equals `0xCDCD` in **21** files.
- Across the 74 files, fraction of zero bytes ranges from **67.83% to 99.50%**.
- Each file's SHA-256 differs: **no exact duplicate files**.
- `M_MAP13.MAP` and `M_MAP14.MAP` share the first four 16-bit words. Exactly
  **174 bytes** differ, in absolute ranges from offset **125,969** through **150,037**.
  These differences have **not** yet been mapped to gameplay or map coordinates.

## Reproducible process (run on private, locally mounted disc image)

```bash
python3 -m tools.saturn_map_survey /private/path/to/track1.bin --output /tmp/map_survey.json
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Output contains metadata, sector-independent statistics, SHA-256 file digests,
and differing byte *counts/offsets* but **never source-game bytes**.

### Next validation gate
Look for stable segmentation using diff offsets, determine whether `.MAP` data
are scene geometry vs battle grid records, and validate against Saturn reference
captures. Do not label a decoded first mission until original map cells/objects,
rules and outcomes have been independently verified.
