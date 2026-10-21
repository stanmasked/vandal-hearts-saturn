# Stage84 — real ISOCD reads in a genuine pinned Yabause process

## Why this stage matters

Stage78/79 compiled and invoked the real pinned historical
`ISOCDReadSectorFAD` function under fabricated host structures.
Stages 80–83 compiled the entire core, launched the original runner,
initialized its subsystems and ran a synthetic SH-2 frame with verified
register changes. Stage84 bridges the remaining gap: invoke the **real
`ISOCD` backend**, as linked into that executable, with actual file
I/O and opt-in CD trace gating.

## Completely invented media

The runtime creates `vh_created_iso_fixture.iso` in a disposable
working directory, consisting of **exactly 4,096 bytes**, two 2,048-byte
sectors with deterministic test-only bytes. The file is not ISO9660,
a bootable Saturn disc, the user's game image, a BIOS or asset extract.
It is deleted when the test process workspace is cleaned up.

The pinned real `ISOCD.Init` sees a file whose length is divisible by
2,048, and assigns fabricated FADs 150–152 (the historical code
uses an inclusive track end). Stage84 directly calls the original
`ISOCD.ReadSectorFAD` pointer. No simulated callback is substituted.

## Controlled numeric logging experiment

| Manual gate state | Request | Expected FAD output |
| --- | --- | --- |
| absent | Valid FAD 150 | none |
| exact ASCII `1\n` | Valid FAD 150 | 150 |
| exact ASCII `1\n` | Valid FAD 151 | 151 |
| exact ASCII `1\n` | FAD 152, synthetic EOF | none |
| malformed ASCII `1\r\n` | Valid FAD 150 | none |
| removed | Valid FAD 151 | none |

Exact expected output (invented values only):

```text
VHCD_FAD 150
VHCD_FAD 151
```

The verifier also checks the 2048-byte user payload begins at offset
16 in the raw sector buffer and distinguishes the two fabricated
sectors. The upstream function returns 1 even for its EOF request,
so suppressed output must come from the new **primary-data fread**
check, not merely the callback return code.

## Build and security boundary

This stage uses exactly pinned public Yabause and LodePNG commits,
validates Git blob IDs and applies our strict full-file Stage80 patch.
The no-media Stage82 init and synthetic SH-2 Stage83 frame smoke tests
also remain part of the same executable. GCC and Clang link the
historical runner in independent CI jobs, with temporary output files.

**Passing does not mean the original Vandal Hearts game ran.**
No authentic Saturn image, BIOS, original executable, graphics,
sound, game map, or private FAD capture is present. No gameplay scene
window is detected; the diagnostic gate is manually toggled. A
repeatable invented FAD trace is not evidence of a first-battle loader.
Those milestones remain blocked by independent private original-game
capturing under Issue #11.
