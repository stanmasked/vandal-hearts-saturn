# Stage89 — two separate BIN files in a Saturn CUE (MODE1 data + CDDA)

## Concrete compatibility problem found

The pinned historical public Yabause revision has a real limitation in
`LoadBinCue`: when it encounters a second `FILE` token, it returns
`Unsupported cue format`. Stage88 tested only a one-file synthetic
CUE and could not establish support for the user's already-supplied
T-9526G English v1.1 two-track CUE/Track1/Track2 set.

Stage02 previously identified a separate raw data Track1 (MODE1/2352)
and audio Track2 (2352-byte sectors) whose in-file pregap is 150 frames,
`INDEX 00 00:00:00` and `INDEX 01 00:02:00`.

## Limited Stage89 implementation

- Accept **only** the exact pinned original public `cdbase.c` Git blob
  as input; retain all Stage79 primary-read and Stage77 gated numeric
  FAD instrumentation.
- Leave the original `LoadBinCue` code intact and use it for ordinary
  one-file images, including Stage88.
- For two or more `FILE` tokens, route to a tightly scoped second parser:
  **exactly two different relative basenames** of `BINARY` files;
  `TRACK 01 MODE1/2352 INDEX 01 00:00:00`; and
  `TRACK 02 AUDIO INDEX 00 00:00:00 INDEX 01 00:02:00`.
- Reject extra tracks, unsupported gap commands, wrong index values,
  path separators/traversals, duplicate filenames, missing files,
  empty/unaligned files and wrong input structure.
- Open both public fabricated BINs read-only, set separate Yabause
  `track_info_struct` FILE pointers and IDs, and use existing
  `ISOCDDeInit` to close both handles. All changes are transiently
  applied to the open-source checkout by the CI workflow; no emulator
  source copy or game assets are committed to this repository.

## Hand-authored data/audio evidence

In public CI the complete executable is compiled with GCC and Clang
and started through the Stage87 pinned private capture wrapper. Every
byte is invented. The generated files contain:

| Track | Test size | Expected FAD and payload |
| --- | ---: | --- |
| Track 1 MODE1/2352 | 2 × 2352 bytes | FAD 150 and 151 |
| Track 2 AUDIO | 152 × 2352 bytes | 150 pregap frames; audible region begins at FAD 302, then 303 |

The real Yabause TOC should identify track starts 150 and 302;
`ISOCD.ReadSectorFAD` must read marker bytes from the *different*
Track1 and Track2 FILE handles, and the opt-in numeric FAD log must
be exactly:

```text
VHCD_FAD 150
VHCD_FAD 151
VHCD_FAD 302
VHCD_FAD 303
```

An attempted EOF FAD 304 must **not** be recorded. The workflow also
runs inherited Stage88 single-file CUE tests to guard backwards
compatibility.

## Scope and limitations

The 150 Track2 in-file pregap frames are skipped in the second
track's addressable INDEX01 content. Stage89 does **not** claim precise
pregap audio playback or subcode reproduction, nor does a synthetic
CDDA-sector read prove actual mixer/console audio output. It tests
track-index addressing and distinct file descriptors only.

Successful CI does **not** prove the original user's disc will boot,
nor identify a Saturn first battle, authoritative battle geometry,
loader-to-resource mapping, animation or original Japanese edition
equivalence. Actual original media remain private and unavailable in
the active task workspace. This addresses a genuine compatibility
obstacle before a later private run; the remaining acceptance gate
is still Issue #11.

## Next steps

Run the tested loader against the existing local-only verified Track1,
Track2 and CUE, with Stage86/87 pinned source/executable preflight,
then observe real game startup and independently correlate first-battle
display/frame checkpoints with bounded numeric CD read captures.
Never put the user's disc, private logs, audio, screenshots or assets
into a public CI job.
