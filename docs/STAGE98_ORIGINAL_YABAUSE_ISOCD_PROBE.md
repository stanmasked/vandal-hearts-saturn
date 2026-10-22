# Stage98 — original Saturn disc read by the genuine pinned public Yabause ISOCD backend

## Why this is a distinct milestone

The original English v1.1 Saturn **Track1, Track2 and CUE** have now been
restored privately from the user's split ZIP volumes and matched the full
Stage02 content hashes. The read-only ISO9660 inventory and candidate
file extents were also verified from the actual disc.

Earlier Stage84–91 proved CD reading under *genuine historical Yabause*
with **invented** disc sectors and one-/two-file CUE. They did NOT prove
that this real game disc opened in the emulator's actual ISOCD backend.
Stage98 supplies an opt-in **read-only real-original-disc probe** which
tests this integration without booting copyrighted Saturn game code.

## Core runner and evidence

The historical Yabause and LodePNG source revisions remain **pinned**.
The new Stage98 instrumentation is chained onto Stages82–89 and Stage91's
strict CATALOG-first two-file CUE parser, with the Stage79 gated numerical
CD callback and no changes to the existing synthetic test modes.

The `vh-private-disc-probe` mode accepts exactly one absolute CUE
argument and, **using actual ISOCD.Init, ISOCD.ReadTOC and
ISOCD.ReadSectorFAD from Yabause**, performs these read-only checks:

| Real image address | Purpose |
| --- | --- |
| FAD 150 | Verify Sega Saturn boot magic from Track1 |
| FAD 151 | Verify another actual Track1 data read |
| FAD 166 | Verify real ISO9660 Primary Volume Descriptor |
| FAD 2479 | Read the Stage02-inventoried `BATL1PRG.BIN` starting sector |
| FAD 76486 | Read the Stage02-inventoried `MAP_1_1C.BIN` starting sector |
| FAD 264652 | Verify the actual first Track2 AUDIO index via the original ISOCD backend |

These sector addresses are source **filesystem metadata**, not evidence
that the original game's loader ever requested them. Sector data, audio,
graphics and assets are **never printed, hashed to stdout or uploaded**;
only a private numeric `VHCD_FAD` log is written with gate controls.

For short invented CI fixtures, only FAD 150, 151 and the fake audio
start are read; the first invented 2352-byte data sector contains a
fabricated Saturn header. A corrupted fake header is rejected. All
older tests from Stages81–91 still execute against the built executable.

## Public compiler output and private original-disc use

GitHub Actions compiles the exact historical pinned public Yabause under
GCC and Clang, tests the fake split CUE, then uploads **only the public
instrumented runner executable** as a temporary artifact
`stage98-public-linked-yabause-gcc` or `-clang`. Public CI **never**
sees the user's original Track1, Track2, CUE, ZIP volumes, ROM assets,
BIOS, screenshot files or private CD read logs.

The private local operator may download the public-only runner artifact,
verify its SHA-256 independently, and run:

```bash
mkdir -m 700 /private/saturn-iso-probe
python3 -m tools.verify_private_original_yabause_iso_probe \
  --runner /private/public-yabause/yabause \
  --runner-sha256 '<independently-confirmed-binary-sha256>' \
  --track1 /private/saturn/original-track1.bin \
  --track2 /private/saturn/original-track2.bin \
  --cue /private/saturn/original-disc.cue \
  --private-dir /private/saturn-iso-probe
```

All paths and hash placeholders in this example are **not private user
filenames or actual values**. Stage98 requires full original Stage02
source hashes and ISO9660 boot/inventory preflight, and rehashes all
sources and the executable after the child exits.

A successful local pass would mean the **actual original disc's data
and CDDA sectors were opened and read by Yabause's genuine ISOCD
backend**, not just by a standalone Python ISO parser. A protected
numeric-only private receipt is emitted, with explicit false flags for
game boot, first-battle identification and loader-to-map causality.

## Not a game boot

This headless runner's opt-in diagnostic mode initializes Yabause core
and CD backend, but it does **not** load real BIOS, execute Saturn game
code, advance to a first-battle screen or synchronize CD FAD events to
emulated frame counters. Those conditions require the next separate
stage, using actual gameplay observation, and remain the active Issue
#11 acceptance gate. A successful Stage98 probe **must not** be
described as a playable remake or a finished first mission.
