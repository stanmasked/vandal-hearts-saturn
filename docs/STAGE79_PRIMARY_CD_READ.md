# Stage79 — distinguish raw CD data from subcode read success

Stage78 proved our gated numeric-only read logger compiled against the
**actual pinned** public \`ISOCDReadSectorFAD\` callback (Yabause commit
\`7e38821dbac265490f115e163c523a939acda759\`, Git blob
\`d56d5dd1941b553c0ede111a83fcf8e50dbecb45\`). The harness used
invented 2352-byte sectors only.

## What changed

In this historical upstream function, the \`num_read\` variable is reused:
the 2448-byte branch can assign it first from the 2352-byte primary
data read and again from a 96-byte subcode read. Consequently, a
successful subcode read could make \`num_read > 0\` even when the main
2352-byte sector was absent. That is a false positive for a numeric
trace that is supposed to reflect *primary CD data* consumption.

The Stage79 verifier first uses the Stage78 source-pin and gated patch,
then applies a fail-closed **pinned-layout-only** rewrite:

- An independently captured \`vh_primary_read\` records the results
  of each of the five upstream primary-data \`fread\` sites across
  the 2352-, 2048-, and 2448-byte modes.
- Only \`vh_primary_read == 1\` may emit \`VHCD_FAD <number>\`.
- Every expected read pattern, its exact multiplicity, and the
  single original gate condition are checked before compilation.
  An upstream layout change rejects the patch rather than guessing.
- The real upstream callback is compiled by GCC and Clang against
  synthetic tracks. It is not a compiled whole Yabause emulator.

The additional fabricated-sector branch matrix checks:

| Synthetic scenario | Expected trace |
| --- | --- |
| Existing gated 2352-byte successes (152, 153) | both emitted |
| 2448 mode: 2352-byte primary data absent, 96-byte subcode present (200) | suppressed |
| 2448 mode: primary + subcode both present (200) | emitted |
| 2048 mode: absent and present user-data payload (300) | only present emitted |
| 2448 mode: absent and present full-width payload (400) | only present emitted |
| Malformed/closed capture gate, out-of-file read | suppressed |

Expected synthetic receipt:

\`\`\`text
VHCD_FAD 152
VHCD_FAD 153
VHCD_FAD 200
VHCD_FAD 300
VHCD_FAD 400
\`\`\`

## Boundaries

This is **host-side instrumentation verification**, not original Vandal
Hearts Saturn execution. Pinned upstream source is public GPL software
fetched transiently in CI and not committed to this repository.
No original game image, BIOS, assets, real disc sectors, or traces appear
in the test fixture or are uploaded. A successful host read callback does
not prove SH2 loader consumption, scene synchronization, or correct
resource interpretation. The capture gate remains manually controlled.
An actual emulator boot and independently observed battle are still
blocked under [Issue #11](https://github.com/stanmasked/vandal-hearts-saturn/issues/11).

The rewrite addresses the **primary sector payload** result; it does not
claim to verify subcode correctness, every low-level I/O condition
(e.g., seek errors), or Saturn gameplay semantics.
