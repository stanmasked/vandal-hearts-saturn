# Stage 28 — Bound optional X11 input probe; do not stall emulator lifecycle

## Failure evidence from real NeXium jobs

Stage 23 run #39397952128 and Stage 24 run #39399247340 both successfully compiled Nintendo Switch NRO files and captured an initial NeXium screenshot. However, the launch step subsequently timed out after **110 seconds** (GNU `timeout` code 124). Stage 24's saved `input-probe-status.txt` says `input_attempted=Right dispatch=failed`, so that run progressed past attempted input, but then hung before a clean exit. Stage 23 has no input receipt. These are real observations, not proof of one unique underlying cause.

Potential causes include waiting for X11 window activation (`windowactivate --sync` under bare Xvfb, often without a window manager) and the earlier Bash EXIT trap waiting indefinitely for an emulator process that ignored TERM. Stage 27 already fixes the latter with bounded graceful WM_DELETE closure and final host-log phase snapshots.

## Stage 28 correction

- **Remove `xdotool windowactivate --sync` entirely**: it can block on an X11 window-manager activation that may never arrive.
- Send an optional `Right` directly to the already observed X11 window using a four-second `timeout --kill-after=1s`.
- Bound the optional post-key ImageMagick screenshot with an eight-second `timeout --kill-after=1s`.
- Failed/timed-out input dispatch is recorded as `input_attempted=Right dispatch=failed` and **does not block the mandatory screenshot or lifecycle evidence**. It does not prove input delivery to the Nintendo Switch guest.
- Existing Stage 27 graceful WM_DELETE, pre-close log snapshot, strict fatal host-log health check, and phase audit remain in force.

## Validation

Extended `tests/test_nexium_lifecycle.py` with an intentionally stalled xdotool `key` mock (30-second sleep). The launcher exits after the four-second optional-input timeout, saves the attempted-input receipt and completes graceful teardown. The previously existing 12 tests still pass: **13/13** total local Python tests. Bash syntax check passed. No actual console or emulator is simulated as a successful guest boot.

## Required next verification

GitHub Actions must rerun the newest head and produce real input-probe and lifecycle artifacts. Any X11/winit panic will still fail the stability gate. The original Sega Saturn first battle and asset semantics remain unimplemented; no protected game data is committed.
