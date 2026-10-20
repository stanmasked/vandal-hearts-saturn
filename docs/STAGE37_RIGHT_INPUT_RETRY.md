# Stage 37 — Bounded, screenshot-verified X11 Right retry

## Grounded reason

Stage36 ROM-free Nintendo Switch NRO produced several successful actual NeXium guest framebuffer/64-bit battle-checksum runs and clean zero exit through EWMH WM_DELETE. In an earlier repeat, `input_attempted=Right screenshot=ready` was recorded but the actual yellow isometric cursor was unchanged. A successful xdotool call only demonstrates host dispatch, not that the Switch guest consumed the event.

## Behavior

New `scripts/nexium_right_probe.sh` handles the optional X11 Right check, invoked by `nexium_capture.sh` only after the initial real framebuffer image exists. It sends one bounded X11 Right key, sleeps one second, captures `nexium-after-right.png`, and calls the **existing actual screenshot analyzer** `tools.nexium_cursor_motion` to check visible displacement.

If the first screenshot proves Right movement, stop immediately with `selected_attempt=1`; do **not** send a second key. If it does not, request focus without `--sync` (bounded to 2 seconds), send one more bounded Right key, take a separate `nexium-after-right-retry.png`, and inspect that second screenshot against the original pre-input frame.

Only when second screenshot proves movement does it replace the canonical `nexium-after-right.png` for the existing mandatory guest visual CI checks. If neither shows movement, preserve both images and explicit `attempt1/attempt2=no_verified_movement` receipts; **do not claim success** or alter expected battle checksums. The authoritative `tools.nexium_guest_evidence` still fails the job on missing cursor displacement.

Every dispatch/capture has GNU timeout + a kill-after grace. Existing guest state, frame classifier, EWMH shutdown and strict no-panic lifecycle checks remain unchanged. `input-probe-attempts.txt`, `input-motion-attempt-{1,2}.json`, corresponding stderr and any retry screenshot are uploaded in the usual runtime-evidence archive. No Saturn copyrighted content is involved.

## Tests

Five new subprocess-level synthetic tests execute the real Bash probe using mock `xdotool` and `import`, but use the **production** `tools.nexium_cursor_motion` Python implementation on generated 1280×720 PNG screenshots. They cover immediate response/no retry, delayed response and selecting the second screenshot, zero response despite two dispatches, invalid X11 ID, and shell syntax.

**5/5 passed locally** with Pillow. The tests never treat a dispatched key by itself as successful guest input. Stage37 CI on the new head is needed to verify the behavior with a real NeXium build.

## Scope

These are ROM-free synthetic input diagnostics, not Joy-Con/Pro Controller hardware testing or authentic Sega Saturn first-mission restoration. The original BIN/CUE, maps, character art and sound remain privately held and absent from GitHub.
