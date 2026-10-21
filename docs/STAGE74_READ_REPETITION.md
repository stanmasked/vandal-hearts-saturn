# Stage74 — repeated read gate: candidate comparison without false authenticity

Stage73 added metadata-only ISO file-extent intersection with a private
first-battle-entry read trace and a menu-control trace, plus an explicit,
bounded Saturn CD-block FAD → logical-LBA converter.

A single capture is a weak basis for choosing an original-game resource:
cached reads, boot resources, incomplete controls and accidental intersections
can look battle-specific. Stage74 tests *consistency of candidate-sector
observations across multiple submitted captures*. No authentic captures are
included in this repository and it is **not a first-battle decoder**.

## Local/private workflow

The Stage73 input trace can contain multiple runs per phase. At least **two
`first_battle_entry` runs and two `menu_control` runs** are required for
a numeric repetition report to be marked ready. Each run is an array of
logical ISO sector reads after explicit FAD normalization, if needed.

```bash
python3 -m tools.saturn_read_repetition \
  --inventory /private/saturn_iso_metadata.json \
  --trace /private/battle_and_menu_reads.json \
  --output /private/read_repeatability.json
```

For each Stage65 allowlisted filename, the analyzer intersects *exact sectors
read in every battle-entry run*. It subtracts the union of all sectors read in
menu-control runs and flags overlapping ISO9660 file extents. The report
contains only allowlisted filenames, aggregate counts and fixed outcome codes.

## Crucial evidence limits

- The report flags `numeric_repetition_gate_ready=true` only when a
  sufficient number of **submitted** runs exist. It cannot prove that
  those runs represent independent executions. Duplicating the same file's
  events across runs can satisfy the numerical gate.
- Missing reads from an incomplete menu control do not establish exclusive
  battle usage.
- Repeated read overlap is not proof of a loader relationship, correct file
  interpretation, real first-battle geometry or unpatched Japanese source.
- Even a `repeated_battle_differential_candidate_only` status requires
  external capture provenance, screen synchronization, controlled source
  editions and code/data tracing before authenticity claims.
- FAD/MSF cannot be silently passed as ISO logical-LBA input; use Stage73
  explicit converter and verify the first Track-1 extent.
- Public tests use only invented sector numbers and invented ISO metadata;
  no original media, disassembled executable bytes, translations, game
  content, original first-battle map, or private capture data are included.

This tool narrows private follow-up priorities, **not** the set of assets
considered authenticated. Research gates remain in Issue #11.
