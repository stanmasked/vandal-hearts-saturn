# Stage94 — private source-to-emulator handoff without stale success receipts

## Purpose

Stage93 verified a complete private Saturn Track1/Track2/CUE against Stage02
content hashes and ISO9660 boot metadata. Stages86/87 independently verified
private gated FAD captures and executable hashes. **Stage94 makes these two
checks one sequential local operation** rather than allowing a separate
preflight to be treated as proof of media identity during an emulator run.

The Stage94 operator tool is `tools/saturn_private_boot_handoff.py`.

## Private procedure

This cannot run on the original Vandal Hearts disc in current ChatGPT
tools: Track1 is over the connected Drive's 256 MiB full-file download limit.
It requires three existing local privately owned files and an instrumented
Yabause executable whose SHA-256 the operator independently pins.

Use a fresh empty directory outside every Git checkout with mode 0700.
Example *placeholder* command:

```bash
mkdir -m 700 /private/saturn/capture-handoff-01
python3 -m tools.saturn_private_boot_handoff \
  --track1 /private/saturn/track1.bin \
  --track2 /private/saturn/track2.bin \
  --cue /private/saturn/disc.cue \
  --private-dir /private/saturn/capture-handoff-01 \
  --phase menu_control --runner-sha256 <separately-pinned-sha256> \
  -- /absolute/path/to/instrumented-yabause \
  <required-local-yabause-arguments> /private/saturn/disc.cue
```

This example does not imply the real source filenames or emulator arguments
are those exact placeholders. The private operator must use their actual
locally installed runner and instrumented CD gate. Stage77 manual controls
can open/close the private FAD gate while the child process is running.

## Verification sequence

1. Refuse reused, unsafe or repository-contained work directories, nonabsolute
   source and executable paths, an incorrect 64-hex executable pin, and
   missing exact CUE argv token.
2. SHA-256-pin the locally supplied executable **before** launch.
3. Execute complete Stage93 preflight: hash **all three original files**
   against Stage02 pins before and after ISO9660 metadata inspection; verify
   both CUE indices, Saturn boot format and inventory counts.
4. Run Stage86/87's guarded local capture in the same protected workspace.
   It checks the executable plus all three source-file hashes/identities
   before/after the subprocess, refuses a nonzero exit or unfinished gate,
   and requires a canonical numeric-only FAD log.
5. Re-run **full Stage93** after the child exits. Require identical bounded
   metadata/identity claims and recheck the executable fingerprint again.
6. Only then write a new private `source-to-capture-receipt.json` (0600),
   containing Boolean integrity facts and numeric event count only.
   No private file paths, full hashes, sector bytes, CUE catalog number,
   game asset names, frame images, credentials or original media are exported.
7. If the final postflight fails **after** Stage86 emitted its receipt,
   revoke that earlier lower-assurance receipt rather than leaving a
   misleading positive outcome. A numeric trace may remain local for
   forensic inspection but must not be treated as an authenticated capture.

## What passing means and does not mean

A passing operator run establishes consistency of locally pinned media and
executable identity **around** a declared CD capture subprocess. It does NOT
prove the executable's signed build origin, that the CUE was actually opened,
that real Saturn game code booted, that the scene was the first battle, that
screenshots were synchronized with the reads, or any loader/map authenticity.
Those remain explicit **false** flags in the final receipt. It also cannot
absolutely eliminate a sufficiently privileged process that changes and then
restores files between independent hash passes.

Stage94's public CI uses only an invented 22-sector Saturn-shaped Track1,
invented Track2/CUE and a tiny synthetic Python executable with fake numeric
FAD events. It tests mutation during child execution, postflight failure
receipt revocation, bad runner pins, wrong CUE tokens, unsafe workspaces,
unclosed gate and unsolicited files. These tests do not bootstrap or run
the real user-owned original game.

**Critical blocker remains:** original English v1.1 Track1 has not yet been
downloaded and rehashed in this session because of the connector limit.
Stage92 provides an independent local OAuth/Range method; Stage93/94 can
be used only after that full private source check. Issue #11 stays open
until original-game first-battle frames and CD reads are independently
observed together.
