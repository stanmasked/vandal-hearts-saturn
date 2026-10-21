# Stage90 — Stage02-pinned private two-track CUE and media preflight

## Actual private source discovery

The user's already supplied **English v1.1** Sega Saturn data are present
in a connected private Google Drive folder called `VH-Saturn`, with
three separate files (Track1 RAW MODE1/2352, Track2 CDDA RAW, and CUE).
This eliminates any need to request the same upload again.

During this private session, the **305-byte CUE** and the **2,102,688-byte
Track2** were read locally and their SHA-256 fingerprints matched the
pinned Stage02 reference **exactly**. The real CUE has eight directives:

- `CATALOG` followed by the disc catalog number;
- `FILE` pointing to Track1, `TRACK 01 MODE1/2352`,
  `INDEX 01 00:00:00`;
- a second `FILE` pointing to Track2, `TRACK 02 AUDIO`,
  `INDEX 00 00:00:00`, `INDEX 01 00:02:00`.

No original CUE text, private Drive URL, audio sector contents or binary
data are committed to this repository.

The connected Drive metadata confirms Track1's previously cataloged
size of **621,755,904 bytes**. However, the raw-file connector has a
**268,435,456-byte per-file download limit**: attempting to access the
complete 621,755,904-byte Track1 was rejected. Stage90 therefore does
**not** claim to have rehashed Track1, opened its original sectors or
booted the source game. The Track1 SHA-256 pinned in Stage02 remains the
necessary separate private verification.

## Private numerical disc layout — metadata only

From the real CUE grammar and Track1/Track2 declared sizes:

| Quantity | Value |
| --- | ---: |
| Track1 data frames | 264,352 |
| Track1 FAD interval | 150–264,501 |
| Track2 total raw frames | 894 |
| In-file Track2 pregap frames | 150 |
| Track2 active CDDA frames | 744 |
| Track2 INDEX 01 FAD | 264,652 |
| Track2 last active FAD | 265,395 |

These are **calculated addresses** from known sizes and CUE index labels,
not an original game runtime read trace.

## New preflight

`tools/saturn_private_split_cue_preflight.py` parses a deliberately
strict eight-directive CUE format, rejects unknown/extra commands,
unsupported index timing, extra files, path traversal, bad sector
alignment, integer/bool confusion and track address overflow.

It checks full-file SHA-256 against Stage02 pins for each locally
available input. A remote metadata size or a Drive filename is never
substituted for hashing the actual Track1 bytes.

A private partial check may use `--track1-metadata-size` and
`--track1-metadata-name` when Track1 cannot be accessed locally.
Its output has `local_media_ready_for_capture=false` and blocker
`TRACK1_CONTENT_NOT_LOCALLY_HASH_VERIFIED`. Once the real Track1
is privately available, supply `--track1` to require full SHA-256,
and only then may the local preflight report source completeness.

Example private invocation (paths are placeholders):

```bash
python3 -m tools.saturn_private_split_cue_preflight \
  --cue /private/saturn/disc.cue \
  --track2 /private/saturn/track2.bin \
  --track1 /private/saturn/track1.bin
```

All CLI output is only bounded numeric counts, Boolean flags, fixed
blocker codes, and explicit false authenticity flags: no filenames,
sector data, original disk hashes, directory locations, or scripts.
Public CI exercises solely fabricated CUE and invented media digests
on Python 3.11 and 3.13. It neither downloads nor copies the real disc.

## What this enables — and what remains missing

Stage89 already validated two-file CUE support under the genuine pinned
public Yabause with invented data/audio sectors. Stage90 establishes
that the **actual private CUE grammar matches that limited parser**
and confirms real Track2/CUE identity.

The remaining hard blocker is Track1 content access through a
private mechanism that can handle files larger than 256 MiB, followed
by a clean source hash comparison, private Yabause boot, synchronized
screen/frame observation, real first-battle FAD traces, and an
independently verified loader-to-map relationship. Do not upload
the original disc or extracted assets to public GitHub or CI, and
do not treat an English v1.1 translation patch as an authenticated
unmodified Japanese master.

Original first-battle acceptance remains Issue #11.
