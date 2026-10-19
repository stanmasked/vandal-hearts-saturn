# Stage 05 — Saturn MAP structural research

Source: user-owned Sega Saturn T-9526G **English v1.1** image, a translated/modified release.
Only metadata/diagnostics and synthetic test fixtures are committed. No copyright-protected game content is published.

## Confirmed filesystem-relative .MAP observations

- All 74 \`.MAP\` files are 170,624 bytes (\`0x29A80\`).
- Exactly 3 long ranges contain **only zero bytes across every one of the 74 files**:
  - \`[0x0E942, 0x11801)\`: 11,967 bytes
  - \`[0x1C610, 0x1E800)\`: 8,688 bytes
  - \`[0x23804, 0x24401)\`: 3,069 bytes
- There are 4,096-byte occupancy windows which are always empty: \`0x0F000\`,
  \`0x10000\`, and \`0x1D000\` (all 74 samples).
- The windows starting at \`0x00000\`, \`0x11000\`, \`0x1E000\` and \`0x24000\`
  contain nonzero data in all 74 samples. These are **not proven segment headers**.

## Controlled comparison: M_MAP13.MAP versus M_MAP14.MAP

- 174 differing bytes (174 distinct 16-bit word positions), **all odd offsets**;
  no changes at even offsets.
- Nonzero/zero masks are identical at **every byte position**.
- First difference \`0x1EC11\`, last difference \`0x24A15\`.
- All changes occur in exactly three 4 KiB windows:

| Window start | Differing bytes |
| --- | ---: |
| \`0x1E000\` | 21 |
| \`0x1F000\` | 84 |
| \`0x24000\` | 69 |

These observations make a shared record structure **plausible**, but do not prove
that the differences describe map cells, palette values, textures or geometry.
No authentic Saturn map decoder or first battle is implemented yet.

## Reproduce locally, without uploading any original game data

\`\`\`bash
python3 -m tools.saturn_map_structure "/private/path/to/track1.bin" \
  --output /tmp/vhsaturn_stage05_structure.json
python3 -m unittest discover -s tests -p 'test_*.py' -v
\`\`\`

The JSON output is limited to offsets, counts, ranges, product code, volume title
and diagnostics; it contains no source game data. The 7 new Python tests use
synthetic bytes only (20 Python tests total).

## Next gate

Examine boundary/header consistency and cross-reference related .BIN / .DAT
assets using private media and live Saturn reference behavior. Define a neutral
map schema **only after** validating tile dimensions, geometry, and event links.
Do not equate the altered English v1.1 assets with original Japanese bytes.
