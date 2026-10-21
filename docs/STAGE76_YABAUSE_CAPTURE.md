# Stage76 — local Yabause CD read tracing (FAD only)

Stages73–75 validate private numeric sector-read traces, but do not capture real Saturn runtime reads. Stage76 prepares a deliberately limited opt-in instrumentation hook for Yabause ISO virtual drive callback `ISOCDReadSectorFAD` in `yabause/src/cdbase.c`.

Source context: https://github.com/Yabause/yabause/blob/master/yabause/src/cdbase.c and https://wiki.yabause.org/index.php5?title=CDBlock.

## Apply locally

1. Keep the Saturn BIN/CUE image, emulator BIOS and all traces private. Obtain a separate, local Yabause checkout.
2. Produce a patched copy, leaving upstream untouched:

```bash
python3 -m tools.saturn_yabause_cdbase_hook --source /private/yabause/yabause/src/cdbase.c --output /private/cdbase-instrumented.c
```

3. Review the modified file, insert into your **local** Yabause checkout and build that third-party emulator independently. This project has not built or run full Yabause in CI.
4. Launch the instrumented emulator with `VH_SATURN_FAD_LOG=/private/battle01.vhcdlog` (or a separate menu-control filename). If the environment variable is unset, the hook does nothing. Successful ISO-sector callback reads append lines like `VHCD_FAD 160`. No sector contents are emitted.
5. Keep separate logs from at least two battle-entry sessions and two menu-control sessions and privately record their source edition, startup conditions and gameplay context.

**Limit:** This hook cannot distinguish menu from battle by itself. It records reads throughout its active process. A complete cold-boot run is not a precisely isolated first-battle-entry window. Do not infer loader identity or exclusive first-battle reads without controlled phase-specific timing and screen evidence.

## Normalize locally

```bash
python3 -m tools.saturn_yabause_fad_log --inventory /private/iso-metadata.json --battle-log /private/battle01.vhcdlog --battle-log /private/battle02.vhcdlog --menu-log /private/menu01.vhcdlog --menu-log /private/menu02.vhcdlog --output /private/normalized.vhcdtrace.json
```

The parser checks numeric-only events, input uniqueness, per-run limits, valid Track-1 FAD boundaries and sufficient phase counts. The existing Stage73 normalization performs the explicit FAD-to-ISO-LBA conversion (subtract 150). Reads from outside Track 1, including audio, fail closed instead of being discarded. Stage74 and Stage75 can then review the private normalized trace and capture sidecar.

## What has and has not been tested

- Public CI compiles and executes a **fabricated C callback** containing the injected diagnostic logic and tests its numeric output, success-only behavior and opt-in gating.
- CI does not compile full Yabause, boot the original game, capture CD reads from a Saturn game, authenticate source editions or reconstruct the first mission.
- A successful callback call is a host ISO-sector read, not conclusive proof that game code consumed a file or decoded a map. Caching, read-ahead and hardware timing may differ.
- The original English v1.1 user image is not uploaded to GitHub. Local `*.vhcdlog` and `*.vhcdtrace.json` files are ignored.
