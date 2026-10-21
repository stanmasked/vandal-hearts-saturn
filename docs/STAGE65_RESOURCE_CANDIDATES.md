# Stage65 — Saturn resource candidate crosswalk (metadata only)

## Source status
The user supplied the English v1.1 translation-patched Saturn source set
(split Track 1 archive parts, Track 2 audio BIN and CUE). The existing private
inventory is documented in `docs/STAGE02_DISC_FINDINGS.md`. This stage does
not request or publish those files, and it does not claim a fresh raw-byte pass
because the track binaries are not materializable in the current workspace.

## Metadata already in the saved disc catalog
- `MAP_1_1C.BIN`: 84,480 bytes at ISO LBA 76,336.
- `MAP_1_1P.BIN`: 512 bytes at ISO LBA 76,378; the extents are adjacent when
  rounded to 2,048-byte ISO user sectors.
- `BATL1PRG.BIN`: 245,760 bytes at ISO LBA 2,329.
- `BATLEPRG.BIN`: 245,760 bytes at ISO LBA 2,449; these extents are also
  adjacent by sector count.
- `EV01.PRG`: 13,664 bytes at LBA 15,972; `EVENT01.DAT`: 1,510 bytes at
  LBA 16,669. Matching `01` in names does not establish a loader relation.
- `M_MAP01.MAP`: 170,624 bytes at LBA 80,724.
- The 74 MAP files are 34 `M_MAP`, 22 `M_IVE`, 17 `M_KEY`, and one
  `M_SHOW`; all are 170,624 bytes.

## What Stage65 adds
`tools/saturn_resource_candidates.py` reproduces this metadata inventory from
a private Track 1 BIN and groups likely related names. It emits names, sizes,
ISO extents, sector adjacency, map-family counts and explicit unverified status
only. It never extracts or writes resource payloads. Tests use synthetic
metadata and assert that matching names/adjacent extents are never upgraded to
verified game semantics.

Run locally:
```bash
python3 -m tools.saturn_resource_candidates /private/path/to/track1.bin \
  --source-label "English v1.1 translation-patched" \
  --output /private/vh_resource_candidates.json
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Next gate
Inspect the candidate resources locally and establish their actual loader
relationships from executable/event code and controlled Saturn runtime
observation. The current data does **not** identify the first battle map, decode
terrain/height/collision, or prove that English v1.1 matches the unpatched
Japanese master.
