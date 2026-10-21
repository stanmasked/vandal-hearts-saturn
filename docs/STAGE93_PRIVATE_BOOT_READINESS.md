# Stage93 — complete private Saturn source and ISO filesystem readiness gate

## Purpose

Stage92 introduces a local-only Google Drive Range method for obtaining the
user's **previously supplied** English v1.1 Saturn Track1, whose complete
size is above the current ChatGPT Drive connector's download limit. Stage92
checks the whole-file SHA-256 before exposing its output.

Stage93 composes the established private source-checking tools into a
**single fail-closed pre-boot gate**. It is intended to run only when all
three original local files — Track1 MODE1/2352, Track2 CDDA and CUE — are
available on a private trusted machine. The original Track1 was **not**
available in the current task environment, so Stage93 does not establish
that the real game booted or even that current local Track1 bytes were read.

## Local operator procedure

After obtaining the owned Track1 using Stage92 or an existing authorized
private copy, place it under the **exact basename referenced by the owned
CUE**. The CUE and Track2 must also be local and readable without symlinks
or unexpected modifications. Do not upload, commit or paste their content.

Run the new private check with the existing local sources:

```bash
mkdir -m 700 /private/saturn-stage93
python3 -m tools.saturn_private_boot_readiness \
  --track1 /private/saturn/actual-track1-name.bin \
  --track2 /private/saturn/actual-track2-name.bin \
  --cue /private/saturn/actual-disc-name.cue \
  --receipt /private/saturn-stage93/source-readiness.json
```

All paths above are **placeholders**, not names copied from the private
Drive metadata.

The check does not launch Yabause, nor enable CD captures. It requires:

- Full Stage02 SHA-256 and size pins for **all three** real files, not just
  Drive metadata. It rejects missing or symlinked inputs, including files
  inside a Git checkout.
- The exact Stage90 eight-directive two-track CUE and safe matching file
  basenames.
- Valid read-only RAW MODE1/2352 Saturn boot framing, ISO9660 primary
  volume descriptor, volume label and product code `T-9526G`.
- Agreement with the already measured Stage02 metadata: 264,352 logical
  data sectors, 848 files, two directories and the independently recorded
  extension counts.
- Presence of two Stage02 inventory candidate **filenames only** —
  `MAP_1_1C.BIN` and `BATL1PRG.BIN` — without opening or publishing
  their contents, and every file extent inside Track1 boundaries.
- A second full source SHA-256 and file identity comparison **after**
  reading ISO metadata; a concurrently mutated source causes failure.
- If explicitly requested, a new 0600 numeric/boolean-only receipt in
  an empty, protected 0700 directory outside Git; the receipt contains
  no source paths, hashes, file lists, game resource bytes or screenshots.

The method intentionally reads the ISO directory metadata (needed to
verify Stage02) but does not extract or export copyrighted assets.

## Test evidence

Stage93 public CI builds a **22-sector invented RAW MODE1/2352 test image**,
a second invented AUDIO BIN, and a strictly matching artificial CUE.
The image has a fabricated Sega Saturn header and one invented ISO file.
The expected counts are injected only in these unit tests, never changed
in the real preflight defaults. Tests exercise correct integrity, wrong
hashes, missing or symlinked Track1, altered Track2/CUE, invalid ISO
extents, incomplete expected inventories, unsafe receipts and source
mutation during inspection.

The synthetic-only tests also rerun Stages92,90 and the original Stage02
ISO parser regressions under Python 3.11/3.13. No public workflow
downloads real Drive content or receives private OAuth secrets.

## Evidence boundary

A successful real local run of this tool would prove **private media
identity and bootable-format readiness**, not successful Saturn emulation,
first-battle execution or correct loader/resource attribution. Every
receipt explicitly preserves
`original_game_boot_observed=false`,
`real_first_battle_scene_observed=false`,
`frame_synchronized_fad_read_verified=false`, and
`source_japanese_master_equivalence_verified=false`.

Next after a genuine private Stage93 pass: run the instrumented Yabause
under Stage86/87's SHA-256-pinned read-only process wrapper, observe a
real frame externally, then capture independent bounded menu and
first-battle CD windows for Stage73–75's hypotheses. Do not elevate a
self-reported phase name or a synthetic sector hit into a source-game
authenticity claim. Issue #11 remains the acceptance gate.
