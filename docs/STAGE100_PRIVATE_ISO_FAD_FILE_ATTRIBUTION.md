# Stage100 — actual Yabause game CD FAD reads intersected with original ISO9660 files

## Evidence actually obtained from original private media

The original English v1.1 Saturn Track1/Track2/CUE were previously
verified byte-for-byte against Stage02's SHA-256. Stage98 established
genuine original private ISOCD backend reads through the pinned public
Yabause code. Stage99 went further: actual HLE-BIOS/SH2/CDCORE_ISO frame
execution, with gated `VHCD_FAD` logs and local-only screenshots.

Stage99 original-media private observations:

| Frames | Recorded physical CD events | Unique FAD | Framebuffer |
| ---: | ---: | ---: | --- |
| 12 | 53 | not asserted | 320×224, black |
| 120, first cold process | 305 | 279 | 352×240, black |
| 120, second cold process | 305 | 279 | 352×240, black |
| 600 | 396 | 370 | 352×240, all checkpoints black |

Both independently started 120-frame Yabause processes had exactly
**byte-identical FAD logs, the same ending SH2 PC and identical final PNG**.
The 600-frame runner also produced local checkpoint PNGs at 120, 240,
360, 480 and 600 frames. All were black: **no visually identifiable
first-battle or even title screen has been verified**.

A private local read-only overlap analysis of the **396 naturally
observed** 600-frame FAD events against the **848 original ISO9660 file
extents** found:

| Original ISO filename | Event count |
| --- | ---: |
| `0.BIN` | 172 |
| `BATLEPRG.BIN` | 120 |
| `MOVIEPRG.BIN` | 37 |
| `0.` | 17 |
| No named file extent | 50 |

The last category can include directory/volume sectors and is not
automatically an invalid read. The 600-frame trace contains no events
in the Stage02 candidate first-battle file intervals:
`BATL1PRG.BIN` FAD 2479–2598,
`MAP_1_1C.BIN` FAD 76486–76527, nor active CDDA
Track2 (264652–265395). The Stage98 diagnostic **manually targeted**
candidate sectors and must not be conflated with Stage99's automatic
guest-initiated trace.

The mapping establishes that the actual emulation process accessed
these ISO file address ranges. It does **not** prove a loader routine,
a visible game scene, or video/audio playback.

## Reusable private Stage100 tool

`tools/saturn_private_iso_fad_attribution.py` now codifies this
analysis for later **privately collected** Stage99 and successor runs:

- Require fresh full Stage02 SHA-256/identity checks for original
  Track1, Track2 and CUE, exact Stage90 CUE grammar, and complete
  Stage93 Saturn/ISO9660 inventory constraints before analyzing reads.
- Read only canonical bounded `VHCD_FAD <number>` source callback logs
  from a protected 0700 directory and 0600 regular file; reject
  symlinks, malformed lines and impossible addresses.
- Convert physical FAD to Track1 logical sectors, intersect each
  observation with ALL named ISO9660 file extents; never invent a
  unique owner when extents overlap.
- Separately count events outside file extents, inside CDDA, in the
  data/audio-index gap and within the first-battle candidate intervals.
- Re-verify every source file after inspection; stop on mutation.
- Write the full **filename-metadata-only** overlap analysis to a
  private 0600 JSON. Public console output contains only high-level
  numeric counts and explicit false first-battle proof.

Example with placeholder original paths:

```bash
mkdir -m 700 /private/fad-analysis
python3 -m tools.saturn_private_iso_fad_attribution \
  --cue /private/saturn/disc.cue \
  --track1 /private/saturn/track1.bin \
  --track2 /private/saturn/track2.bin \
  --fad-log /private/run600/fad.vhcdlog \
  --private-output-dir /private/fad-analysis
```

No Track1, Track2, CUE, original screenshots or full real FAD log is
uploaded to public GitHub. Public Python 3.11/3.13 regression jobs use
only an invented 22-sector Saturn-shaped test fixture and fake read
events to check overlaps, shared owners, bad FAD syntax, bad source
hashes and privacy safeguards.

## Acceptance remains open

Even true original CD callback FAD values and a changing emulated PC
do not prove graphics reached a menu or the first battle. The next
work must investigate black framebuffer causes, capture independently
observed real pixels, and correlate verified frame counters with CD
callbacks. Issue #11 remains open; original first-battle map, enemy
stats, movement and combat cannot be asserted from filename overlap.
