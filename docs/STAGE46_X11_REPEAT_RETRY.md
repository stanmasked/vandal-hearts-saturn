# Stage46 — Fail-closed, screenshot-confirmed X11 cursor retries

## Confirmed failure (not a gameplay regression)

[Stage45 GitHub Actions #39482410995](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39482410995) compiled the Nintendo Switch NRO and passed both GCC/Clang. The **actual Stage45 NeXium duel continuation PASSED**: genuine guest screenshots confirmed Scout Cancel → reselect → rejected repeat Y with Raider HP unchanged at 14 and battle fingerprint `9a0233cdc1acffdb`. The existing Stage42/43 guest checks also passed. Yet the **overall workflow failed** because the independent launcher repeat auditor reported **2 of 3** success.

Inspecting [artifact #12292681967](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39482410995/artifacts/12292681967) revealed why trial-02 failed:

- NeXium produced a plausible battle framebuffer, no classified fatal host errors, exit code 0, and a verified clean window-manager shutdown.
- Trial-02's original X11 Right pulse and one focused retry both left the yellow cursor at the exact same screenshot location (`delta_x_pixels=0.0`, `delta_y_pixels=0.0`).
- The corresponding `input-probe-attempts.txt` explicitly said `attempt1=no_verified_movement`, `focus_request=sent`, `attempt2=no_verified_movement`. The audit **correctly failed closed**. An X11 key dispatch is not a verified gameplay action.
- The other two independent trials passed; their Right movement became visible on the second attempt. This suggests intermittent input delivery, but the point of loss cannot be assigned to an exact host, compositor or guest layer on this evidence alone.

## Changes

`scripts/nexium_right_probe.sh` now attempts at most **8 screenshot-observed Right pulses**. It preserves a separate original PNG `nexium-after-right-attempt-N.png` and motion JSON for each actually sampled pulse. A missed (or undelivered) input authorizes an attempt to refocus the window, but **never counts as proof**. If none moves, it records `selected_attempt=none`, does not promote a false screenshot, and the independent CI gates reject the trial. Max-attempts must be 1–8 and is bounded even for custom environment input.

After the first *actual verified* motion, the same screenshot is copied into the legacy `nexium-after-right.png` so established Stage42–45 paths and byte-for-byte visual checks remain compatible. The audit independently requires:

1. Exactly one numeric winning index between 1 and the declared max.
2. Exactly one `attemptN=visible_movement` matching that index.
3. The selected screenshot bytes to equal the promoted `nexium-after-right.png`.
4. The selected motion JSON to report `plausible_right_cursor_movement=true`.
5. The unchanged strict host/frame/lifecycle checks.

Six additional host regression tests cover a first success on pulse six, all eight ignored, out-of-range indices, missing/duplicate wins and historical version-1 parsing. **No requirement is weakened** from 3/3 independently valid launches.

## Scope

This fixes the *repeatable evidence-capture and input retry path* in a ROM-free prototype; it does not fix an identified emulator root cause. The underlying Sega Saturn data and original game are not present and physical Nintendo Switch Joy-Con events are not tested. Independent real NeXium validation of this updated retry sequence is still required.
