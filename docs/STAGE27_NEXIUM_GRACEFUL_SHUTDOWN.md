# Stage 27 — Graceful NeXium shutdown and pre/post-close host-log evidence

## Existing verified facts

Previous run #39396848917 generated a real NRO and a visible ROM-free tactical board in NeXium, but its final host log also contains a Rust/winit panic and `Connection(IoError)` from X11. Because the earlier launcher terminated NeXium directly at shell exit and did not snapshot host logs, we cannot prove whether the panic occurred during play or during X server teardown. A screenshot passing the color check is not a stability test.

## Changes

1. Replace unconditional immediate `kill` after successful capture with a graceful X11 `xdotool windowclose` request, while keeping Xvfb alive until the NeXium process exits.
2. Save `runtime-evidence/nexium-log-before-close.log` immediately after screenshot/optional input probe and **before** sending any window-close request. Preserve the full `nexium.log` and `lifecycle-status.txt` with attempted graceful close, any forced fallback, and process exit code.
3. Bound the shutdown wait to 8 seconds by default (integer-configurable via `NEXIUM_CLOSE_WAIT_SECONDS`, range 1–30). If the GUI doesn't exit, terminate the process only as a fallback and **fail the lifecycle gate** even if a signal handler returns zero. The cleanup trap remains active on early failure.
4. `tools/nexium_lifecycle_audit.py` checks that the before-close snapshot is an exact prefix of the final log. It separately reports fatal categories observed before vs after close request, but **never suppresses panics** from either phase. A valid frame and clean lifecycle are separate requirements.
5. New workflow step runs the phase audit with `if: always()` and saves `runtime-evidence/lifecycle-audit.json` before the existing `if: always()` artifact upload. Existing strict `tools/nexium_log_health.py` continues rejecting fatal host errors.

## Synthetic validation

New `tests/test_nexium_lifecycle.py`: 5 integration cases execute the actual Bash launcher with mock NeXium, xdotool and image capture. They cover normal close, early crash, missing graceful-close support/forced termination, panic present before close, and Bash syntax.

New `tests/test_nexium_lifecycle_audit.py`: 7 tests covering clean lifecycle, before/after panic, mismatched snapshots, forced-termination disqualification, after-close X11 error, and benign ALSA warnings.

**12/12 locally passed** (Python unittest discovery). Bash syntax check also passed. Test media are synthetic placeholders; no original Sega Saturn game content was read or committed.

## Known limits / next checks

This instrumentation does not itself prove that the original X11 panic is fixed: it must be rerun on an actual NeXium build and the two log phases examined. A Rust panic occurring after the close request is still a failure; it merely helps identify shutdown as a likely trigger. Genuine ROM-free guest keyboard/gamepad input remains unverified, and the original Sega Saturn first battle remains unimplemented.
