# Stage85 — two independent real-Yabause synthetic FAD replays

Stage84 proved one actual pinned Yabause process can read two invented
ISO sectors with the manually controlled FAD logger. Stage85 audits the
**reproducibility and isolation** of that evidence across two separate
linked-runner processes, not just a single program's printed success line.

## Exact method

1. Run the complete public-source-pinned Yabause executable from the
   Stage84 workflow under GCC and Clang separately.
2. For each compiler, start two independent `vh-synthetic-iso-read`
   subprocesses, each with its own fresh private-mode directory, HOME,
   gate and trace path. Only a minimal environment is supplied.
3. The upstream runner test constructs exactly two **invented** 2048-byte
   sectors. The expected 4096-byte file contents are independently
   regenerated in Python using the published deterministic formula.
4. Inspect each directory after completion. Exactly two output files are
   permitted: `vh_created_iso_fixture.iso` and `real-iso.vhcdlog`.
   The gate must have been removed. Symbolic links are rejected.
5. Read and byte-compare both generated source files against the
   independent fixture and both traces against the exact numeric-only
   receipt below; independently compute SHA-256.
6. Reject missing, duplicate or misleading runner receipts, extra FADs,
   reordered records, CRLF changes, unexpected binary output, altered
   sector data, and unexpected third files.
7. Ensure both independent subprocess receipts have **identical**
   source and trace hashes and byte counts. Print a small JSON receipt
   with hashes only, and no original sector data.

Expected invented trace for each run:

```text
VHCD_FAD 150
VHCD_FAD 151
```

The job's process timeout is 20 seconds per run plus a 60-second bound
around the two-run audit. The run directories are destroyed after the
check and none of the fabricated ISO content is uploaded as an artifact.

## Claims and nonclaims

A pass confirms repeated **synthetic** ISOCD FAD evidence across
separate Yabause processes, in both GCC and Clang CI, while rejecting
common falsification, gate-state and output-contamination conditions.
It does not confirm correct reading of the user's Saturn image,
disc-file identity, real gameplay, SH-2 resource loading or the
first battle of Vandal Hearts.

Privacy: no Saturn BIN/CUE/ISO, BIOS, save state, original sprite,
screenshot, audio or game map is provided or copied to public CI.
For authentic private CD captures and scene linkage, see Issue #11.
The Stage85 manifest is intentionally marked
`authentic_game_boot_observed=false`.
