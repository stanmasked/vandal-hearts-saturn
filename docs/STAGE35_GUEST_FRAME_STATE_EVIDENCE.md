# Stage 35 — Real Switch guest visual state and input must be assessed independently of host shutdown

## Grounded evidence

GitHub Actions run #39412614156 (Stage34) successfully compiled a native Switch NRO and captured two genuine NeXium screenshots (1279×700, with upper-right visual state markers). The *launch step failed* after the emulator was asked to close its window; the host log has Rust winit X11 `GetGeometry`/`Drawable` panic and exits 101. The pre-close log is clean apart from ALSA warnings, the phase audit marks `fatal_before_close=[]`, `fatal_after_close_request=['rust_panic']`.

Independent inspection of both genuine image files decoded three magenta anchors and the 64-bit guest state. **Before Right: `ae38b0b5ab887f00`. After Right: `ae38b0b5ab887f00`.** No cell was unrecognized. The same artifact includes `input_attempted=Right screenshot=ready`, `plausible_right_cursor_movement=true`, X +72px, Y +34.5px. Cursor movement should not mutate tactical battle state; both assertions are grounded.

## Root cause of CI misreporting

In `.github/workflows/switch-nro.yml`, the mandatory blue/red pawn check and the Stage32/34 state checksum decoder were conditional on the preceding launch step's success. Because the launcher deliberately failed for the **post-capture host panic**, GitHub skipped both important *guest-side checks*, despite real screenshots being available. As a result the job was red without machine-readable results for the guest display and state.

## Fix

1. Run the independent frame-marker check and 64-bit guest checksum decoder using `if: always()`, matching existing lifecycle/panic audit behavior. A missing frame still fails; it never fabricates guest evidence.
2. New `tools/nexium_guest_evidence.py` uses both **existing** production analyzers (`nexium_visual_digest.decode` and `nexium_cursor_motion.evaluate_motion`) and the actual `input-probe-status.txt` receipt. It requires the initial AND post-Right images to encode the golden host battle checksum; requires positive isometric cursor displacement, and requires the real input receipt. No condition alone is sufficient.
3. This strict guest evidence step runs with `if: always()` and writes `runtime-evidence/guest-visual-evidence.json` before unconditional artifact upload, even when launch/host teardown fails. Missing files yield an explicit failure report and a nonzero step.
4. The existing Rust/X11 host-log error check and phase-aware graceful teardown check remain **strict and separate**; this change does not suppress, ignore or reclassify the emulator panic. Successful guest-side images do **not** make the overall NeXium job green.

## Independent local validation

On actual prior Stage34 NeXium screenshots, both checksum decodes were identical to the host golden value with no unrecognized cells, and the existing cursor-motion report confirms X+72/Y+34.5, with input probe receipt `screenshot=ready`. This evidence is from real artifact screenshots, not synthetic replicas.

Seven locally executed mocked orchestration tests passed: positive two-frame audit, missing receipt, no cursor movement, incorrect initial/after battle fingerprint, invalid input receipt and missing screenshot. The real core pixel decoders already have their own Stage34 synthetic and C++/Python cross-language test suites.

## Remaining work

Current head still requires its own host and NeXium GitHub Actions results. We have **not** established clean NeXium GUI shutdown, physical Switch controller reliability or authentic Sega Saturn battle content. Original game assets are still private, not present in GitHub. An emulator exit panic after WM_DELETE remains an external host issue to fix upstream or by safe alternative shutdown, not hide.

