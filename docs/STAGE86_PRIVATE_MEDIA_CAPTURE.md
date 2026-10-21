# Stage86 — privacy-locked capture session preflight for the already supplied Saturn disc

## Purpose

Stages 78–85 validated the actual pinned public Yabause CD reader, independent
GCC/Clang builds and two-process synthetic numeric FAD capture. This stage
prepares a **local-only** way to launch an instrumented Saturn emulator with
strong before/after media identity checks and a strict private log gate.

It does **not** run the original game in public CI. The original Track 1 bytes
are **not mounted** in the current active workspace, so no original-game
capture is claimed by Stage86, even if all synthetic tests pass.

## Immutable source identity from Stage02

The three private source inputs correspond specifically to the previously
inspected English v1.1 translation-patched T-9526G release:

| Input | Expected bytes | Source of reference |
| --- | ---: | --- |
| Track 1 RAW MODE1/2352 | 621,755,904 | Stage02 pinned SHA-256 |
| Track 2 RAW CDDA | 2,102,688 | Stage02 pinned SHA-256 |
| Original CUE | Source length not fixed | Stage02 pinned SHA-256 |

All **three** Stage02 SHA-256 digests are hard-coded in
`tools/saturn_private_capture_session.py` and are independently checked
against the files before and after running the emulator. This prevents
accidentally using a different translation, mismatched Track 2 or changed CUE.
It does **not** authenticate the unpatched original Japanese master.

Create a manifest **outside all Git checkouts**, for example
`/private/saturn/source.json`:

```json
{
  "schema_version": 1,
  "product_code": "T-9526G",
  "release_kind": "translation_patched",
  "files": {
    "track1": "/private/saturn/Track1.bin",
    "track2": "/private/saturn/Track2.bin",
    "cue": "/private/saturn/Disc.cue"
  }
}
```

The example paths are placeholders, not actual local files. The wrapper does
not locate or re-download the existing media, and does not copy it.

## Private operator workflow

1. Verify the locally installed Yabause executable really contains the
   validated numeric callback from Stage84/85. This stage cannot attest to an
   arbitrary binary supplied after the `--` separator.
2. Create a fresh empty workspace outside every Git checkout, with mode 0700.
3. Launch the local emulator command directly (no shell) through the wrapper:

```bash
mkdir -m 700 /private/saturn/capture-menu-01
python3 -m tools.saturn_private_capture_session \
  --manifest /private/saturn/source.json \
  --private-dir /private/saturn/capture-menu-01 \
  --phase menu_control --timeout 1800 \
  -- /absolute/path/to/your/instrumented-yabause <local-arguments>
```

The wrapper sets `VH_SATURN_CAPTURE_GATE` and `VH_SATURN_FAD_LOG`
to the private workspace, runs the executable without shell interpolation,
and discards process stdout and stderr to avoid recording private game text,
screenshots, debug dumps or disc contents.

When the emulator is open, a **human operator** can open the selected read
interval from another terminal:

```bash
python3 -m tools.saturn_capture_gate \
  --gate /private/saturn/capture-menu-01/capture.vhgate --start
# Perform a locally observed gameplay action during this interval.
python3 -m tools.saturn_capture_gate \
  --gate /private/saturn/capture-menu-01/capture.vhgate --stop
```

Closing the gate before exit is mandatory. The wrapper only accepts
canonical **numeric-only** `VHCD_FAD <number>` lines in ASCII LF form and
rejects arbitrary text, extra files, symbolic links, malformed gates,
nonzero emulator exits, stale/reused workspaces, or altered media.
A failure emits only a fixed code, never paths, asset data or source hashes.

A successful session writes only two local private files:
`fad.vhcdlog` and `private-receipt.json`. The receipt exposes event count,
an opaque session ID, the operator-chosen phase and explicit unverified flags,
but **never source file paths, SHA-256 fingerprints or sector payloads**.
The private directory is neither committed nor uploaded as a CI artifact.

For later controlled comparison, create **at least two separately observed
cold-boot captures of each phase** (`menu_control` and
`first_battle_entry`) with an independently verified emulator/game boot,
then normalize logs with the Stage76 converter and Stage75 provenance
preflight. Their scene synchronization and independence must still be
corroborated by an external observation; unique IDs alone prove neither.

## Limits and safeguards

- The wrapper checks known files **before and after**, including size,
  SHA-256, file device/inode, mtime and ctime. It cannot eliminate every
  possible modification-and-restore race while an emulator runs.
- The launcher does not automatically decide when battle-entry occurs:
  opening a gate proves only operator intent, not source gameplay state.
- The launcher does not guarantee that the specified executable is the
  expected patched Yabause, nor that its command actually boots the disc.
  Validating such claims requires separate runtime attestation.
- The wrapper deliberately rejects unexpected files to prevent unnoticed
  local dumps; configure the emulator not to write backups, BIOS state or
  raw assets to this output directory.
- A pass is **local integrity readiness only**, not original first-battle
  authenticity, evidence of resource-loader identity or Japanese edition
  equivalence. [Issue #11](https://github.com/stanmasked/vandal-hearts-saturn/issues/11)
  remains the authentic-content acceptance gate.

**Public CI tests this tooling exclusively with three tiny invented files
and a synthetic Python subprocess. It never accesses or publishes the user's
real disc.**
