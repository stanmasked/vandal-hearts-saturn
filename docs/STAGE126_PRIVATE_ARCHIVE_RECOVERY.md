# Stage126 — owner-only Stage124 archive recovery and verification

## Status and limits

Stage124 previously produced two original-disc cold boots of 108,000 frames each. The resulting private capture archive was verified locally, but was **not uploaded and independently read back from Google Drive**. It is absent from the current workspace and the owner-only Stage124 capture folder. The original-disc Track 1, Track 2, CUE and the private Stage124 manifest remain in owner-only Drive.

The Stage124 and Stage125 public CI succeeds; this verifies source and the ROM-free prototype, **not** a tactical battle in the original Saturn game. No Stage125 original-disc run has occurred.

## Restore and verify — private environment only

1. Look for the exact original Stage124 archive, or the original untouched raw output directories, in earlier authorized private workspaces. Never upload original media, original screenshots or trace payloads to GitHub or GitHub Actions.
2. Read the Stage124 *original private manifest* in Google Drive. Obtain the original archive byte count and SHA-256 there, not from a newly created receipt. Neither value is hardcoded in the public source.
3. Locally invoke the Stage126 verifier with the recovered absolute archive path and the two independent expected values, using the three flags --archive, --expected-size, and --expected-sha256. The verifier checks digest, byte count, bounded GZIP/TAR integrity, two complete 900-checkpoint cohorts, all required diagnostic sidecars, PNG framing/chunk CRC/dimensions, safe paths, and unchanged archive identity; it never extracts payload into Git. PNG checks verify file structure, not the actual scene or game state.
4. Once and only once the local archive matches the original private manifest, upload it to the owner-only Drive folder VH-Saturn / Private Archives / Stage124 Private Captures and Logs. Preserve the local archive and original raw outputs.
5. Download that exact Drive object into a separate private directory. Repeat Stage126 verification against the original private manifest. Independently confirm Drive file ID and **owner-only permissions**. Record the genuine upload/readback receipt privately outside the Git checkout. Stage125 separately requires that receipt **and the actual downloaded archive** before an original-disc run can begin.
6. If both the original archive and raw output have been lost, do not invent old evidence. A future Stage124 recapture must be treated as a *new experiment*, independently fingerprinted, tested and archived. Its provenance and digest must never be silently substituted for the previously recorded Stage124 capture.

## CI boundary

The only archive produced in public CI is invented synthetic data. The workflow uses a full synthetic 1,800-checkpoint shape and adversarial tests, including corrupt GZIP tails, TAR traversal, symlinks, incomplete checkpoint sequences, missing archives and mismatched digests. No source BIN/CUE, translated disc, private capture, Drive receipt, screenshot, or real private digest is used or uploaded.

Stage126 offline output contains only a bounded metadata report. Its archive_matches_supplied_fingerprint=true field means only that local bytes match the caller-supplied size and SHA-256; this **does not authenticate the original private manifest or the fingerprint's provenance**. A positive local result deliberately includes drive_upload_and_readback_verified=false, because hashing a local file is not proof that Google Drive contains it. Completion of the separate authenticated Drive readback remains a hard prerequisite for Stage125 private runtime.


## Fresh Stage124 recapture packaging (only if recovery fails)

A future *new* Stage124 run is not a restoration of the missing historical
archive. First execute the pinned original-disc paired experiment in the
private workspace and pass the existing independent Stage124 audit. Retain
untouched originals and all raw outputs.

The private `tools/saturn_private_capture_packager.py` requires two
non-overlapping absolute private output directories with exactly 900 checkpoint
PNGs and eight approved sidecars in each. It refuses symlinks, hardlinks,
unexpected files, incomplete checkpoints, source/output overlaps and existing
archive destinations. It streams the 1,816 required files into a fresh
owner-only TAR.GZIP, fixes archive member metadata to safe stable values,
reopens and audits the compressed archive with the independent Stage126
verifier, and never embeds original game media.

In an authorized local private environment only, after Stage124 paired audit:

```sh
python3 -m tools.saturn_private_capture_packager \
  --control "$STAGE124_NEW_CONTROL_DIRECTORY" \
  --enabled "$STAGE124_NEW_ENABLED_DIRECTORY" \
  --archive "$STAGE124_NEW_PRIVATE_ARCHIVE"
```

The command returns only structural metadata. It **does not** certify the
underlying original-disc experiment, identify the original Stage124 archive,
authenticate an independent manifest, upload to Drive, or produce a Drive
receipt. It explicitly sets `historical_stage124_archive_recovered=false`
and `new_private_archive_requires_authenticated_drive_readback=true`.

Every newly generated archive must be assigned its own provenance, audited
against its *new* run manifest, uploaded to the owner-only Drive capture folder,
downloaded back, and reverified before any deletion of working data. Never
reuse the old historical Stage124 SHA-256 or backdate a new record.
