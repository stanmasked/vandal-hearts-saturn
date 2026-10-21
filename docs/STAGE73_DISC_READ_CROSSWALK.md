# Stage73 — metadata-only runtime disc-read crosswalk

## Goal
Identify **candidate** Saturn disc resources actually read during a
controlled first-battle entry. This is distinct from Stage65's static
filename and ISO extent adjacency analysis.

## Private inputs
- ISO9660 metadata JSON from `python3 -m tools.saturn_iso <private-track-1.bin> --list-files --json <private-inventory.json>`.
- Private read observations collected from a trustworthy Saturn emulator or
  hardware trace. This stage does not provide or fabricate a capture.

The read-trace JSON has `schema_version: 1`,
`addressing: "iso9660_logical_data_lba"`, and at least one
`first_battle_entry` run and one `menu_control` run. Each run has nonempty
`reads` entries of the shape `{"lba": 10, "sectors": 2}` (these numbers
are illustrative, **not** original Saturn offsets).

The address convention is strict: ISO file extent LBA is NOT the physical
disc frame count, MSF timestamp, or an implicit +150 conversion. An emulator
that logs physical-sector offsets must be independently calibrated before
its observations are submitted. Controls must use the same source edition,
address mapping and comparable capture window; otherwise the differential
comparison is misleading.

## CLI

```bash
python3 -m tools.saturn_read_crosswalk \
  --inventory /private/saturn_iso_metadata.json \
  --trace /private/saturn_reads.json \
  --output /private/saturn_read_crosswalk.json
```

No BIN/CUE or original payload is read by this tool. It uses only numeric
sector ranges and filenames and emits a report constrained to the
Stage65 allowlist (`MAP_1_1C.BIN`, `MAP_1_1P.BIN`, `BATL1PRG.BIN`,
`BATLEPRG.BIN`, `EV01.PRG`, `EVENT01.DAT`, `M_MAP01.MAP`).

## Interpretation
For every allowlisted file, the report describes whether its sectors were
read in battle-entry, menu-control, both, or neither; how many unique sectors
overlap; and whether the ISO extent overlaps other files. Repeated reads are
counted once for sector coverage, but sessions that touch a candidate
are counted separately. Shared menu-sector reads are excluded from the
`battle_exclusive_sectors` statistic.

**Do not infer more than this.** A read in battle-entry does not prove that
the loader parsed a map, that the resource is the first battle, or that its
contents encode geography, terrain, units or rules. A missing read in a
potentially incomplete control trace also proves nothing. Reports always
state `loader_relationship_verified=false`,
`first_battle_map_identified=false` and
`trace_origin_authenticated=false`.

The user-supplied English v1.1 translation-patched image does not by itself
authenticate the unmodified Japanese master. No source-derived map/scene data,
original media, graphics, scripts, CD audio or private paths are committed.

## Tests and next gate
Synthetic-only tests cover disjoint/control/shared observations, duplicate
ranges, multiple sessions, boundary clipping, ambiguous ISO extents, missing
candidates, invalid LBAs, addressing mismatches and privacy-safe outputs.
After real privately captured traces are available, corroborate observed
sector activity with controlled original Saturn screen/state captures,
and only then try to establish exact runtime loader relationships in Issue #11.
