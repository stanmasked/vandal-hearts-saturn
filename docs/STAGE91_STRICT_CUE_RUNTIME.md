# Stage91 — strict CUE grammar enforced by the real pinned Yabause executable

## Why

Stage89 enabled a narrow CUE format with two different BIN files
(MODE1/2352 data followed by CDDA) and Stage90 validated the structure of
the previously supplied English-v1.1 private CUE. However, the Stage89
parser had a discrepancy: it could ignore unrecognized CUE directives
instead of rejecting them. Before reading the real Track1, the emulator
must fail closed when encountering anything other than the known layout.

## What is implemented

- Continue to pin and verify the *original upstream* Yabause `cdbase.c`
  Git blob, using the Stage80 and Stage89 patchers in order.
- Further restrict only the newly injected two-file parser to exactly
  eight lines, in this order: CATALOG; FILE; TRACK 01 MODE1/2352;
  INDEX 01 00:00:00; FILE; TRACK 02 AUDIO;
  INDEX 00 00:00:00; INDEX 01 00:02:00.
- Require CATALOG to contain exactly 13 ASCII digits; accept LF and CRLF,
  preserving the actual private CUE's CRLF behavior.
- Reject unknown or duplicated directives, incorrect order, extra tokens,
  overlong/truncated lines, paths containing traversal/separators,
  audio index errors and additional files or tracks.
- Leave the historical one-file Yabause CUE path unchanged. Preserve
  Stage79 verified primary-data read accounting, Stage77 manual gate and
  the Stage89 150-frame AUDIO pregap and FAD mapping.

## Evidence collection

The public CI compiles the real Yabause core and runner with GCC and Clang,
using exact pinned historical public Yabause and LodePNG source commits.
It runs all previous synthetic tests (one-file CUE, two-file data+CDDA,
real ISOCD reads and synthetic SH-2 frame), and additionally spawns
**12 fresh Yabause processes** with distinct deliberately malformed,
entirely fabricated two-BIN CUE inputs. All must fail without a success
receipt or FAD log. This is a runtime rejection test, not merely a
Python CUE parser test.

Every fixture is generated in an ephemeral directory and deleted.
No real game bytes, BIOS, images, original CUE, Track1, Track2, maps,
screenshots or source audio enter public GitHub CI.

## Remaining original-content barrier

The actual private CUE and Track2 are already SHA-256 matched to the
Stage02 references, and the original Track1 Drive metadata reports the
expected 621,755,904-byte size. The Google Drive connector cannot
download that Track1 because it exceeds its 268,435,456-byte raw-file
limit; only a separate private local full-byte source hash could
establish current Track1 identity. This stage makes no claim to have
booted the game, reached its first battle or decoded its map.

Maintain Issue #11 as **BLOCKED** pending actual private Track1 access,
an independently verified real emulator/game boot and synchronized
first-battle CD/frame evidence. Do not put that source into public CI.
