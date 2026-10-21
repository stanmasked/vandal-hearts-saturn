# Stage78 — compile a pinned, real public Yabause ISO callback

Stage76 tested a fabricated C function with our numeric-only sector logger.
Stage77 tested gate opening and closing inside that same fabricated callback.
Stage78 closes a different compatibility gap: **fetch a fixed, public Yabause
source revision and compile the real `ISOCDReadSectorFAD` callback after
applying Stage77's gated instrumentation**. This is not a full emulator build.

## Pinned upstream source and reproducibility

- Repository: https://github.com/Yabause/yabause
- Commit: `7e38821dbac265490f115e163c523a939acda759`
- File: `yabause/src/cdbase.c`
- Git blob object: `d56d5dd1941b553c0ede111a83fcf8e50dbecb45`
- The source file is fetched **only from that fixed public GitHub commit** in
  the host GitHub Actions job and its bytes are checked using the Git blob
  hash formula. A changed or unexpectedly sized file fails the check.
- This job downloads no game media, Saturn images, BIOS, screenshots, CD
  logs or content of the user's owned copy.

## Executed host test

The verifier applies `patch_gated_cdbase` to the pinned upstream source,
extracts the now-instrumented **actual Yabause callback function body**,
and compiles it using GCC and Clang independently, with a miniature fake
track table and fabricated raw 2352-byte sectors. It does not link any
other actual game code into its harness.

A single fake process tests successful sector reads **before**, **inside**
and **after** a manually controlled gate interval. It also rejects a
malformed gate and verifies no FAD is written if the upstream function
returns success but `fread` reaches the synthetic end of file.

The expected private-safe receipt is exactly:

```text
VHCD_FAD 152
VHCD_FAD 153
```

These are **invented addresses** and have nothing to do with the original
Vandal Hearts Saturn ISO extents. The verifier reports only the boolean
result and the public upstream commit/blob IDs, not source code or private
media information.

To rerun the public-source-only check on a host with network access:

```bash
python3 -m tools.check_yabause_upstream_callback --cc gcc
python3 -m tools.check_yabause_upstream_callback --cc clang
```

## Evidential boundaries

- This is the **real upstream callback body**, not the whole Yabause
  emulator. Real Yabause link/runtime integration, CD emulator behavior,
  BIOS compatibility, original-game boot and gameplay scene synchronization
  remain untested.
- No original Saturn game file or disc sector was used or distributed.
- `VH_SATURN_CAPTURE_GATE` remains manually controlled. Logging host CD
  callback reads cannot establish the SH2 loader's exact resource decoding.
- The source supplied in an earlier conversation was a translation-patched
  English v1.1 edition. Its equivalence to the unmodified Japanese release
  remains unverified.
- Successful GitHub CI on Stage78 validates the diagnostic patch against
  pinned public code and synthetic data, **not** the authentic first battle.

Only after an independently verified game boot and private synchronized
read trace can we investigate which ISO resources load the first battle
and use real measurements for the remade tactical engine. Track this
under Issue #11.
