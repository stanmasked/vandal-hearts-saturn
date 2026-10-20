# Stage 30 — Reap X11 window manager and isolate GitHub CI event concurrency

## Source of the change

GitHub Actions Stage29 `d502a996` remained queued at review. Its Host `push` run #39404955286 was marked cancelled because the newly introduced same-branch concurrency key was **identical** for `push` and `pull_request` events, and the later PR event displaced it. Both events used the same underlying commit, so this was unintended cancellation rather than superseding stale code.

Also, the Stage29 Xvfb/Openbox wrapper sent SIGTERM to Openbox on exit but never waited for the child to stop before the X server went away. It could leave a WM running after NeXium had exited, potentially complicating shutdown diagnostics. This is a correctness and isolation problem, **not proof that it caused previous Rust/X11 panics**.

## Implementation

1. Host CI concurrency group now includes event name and branch (`host-${{ github.event_name }}-${{ github.head_ref || github.ref_name }}`). Switch NRO uses the analogous `switch-nro-...` key. A newer push cancels stale pushes; a newer PR cancels stale PRs; **push and PR jobs on the same head no longer cancel one another**.
2. The `scripts/nexium_xvfb_session.sh` EXIT trap now requests Openbox SIGTERM, polls the child for up to two seconds, sends SIGKILL only as a final fallback, and always reaps the PID with `wait` before terminating the wrapper. It writes `window-manager-shutdown.txt` with either `window_manager_reaped` or `window_manager_forced_sigkill`.
3. A WM requiring forced SIGKILL **fails** a previously successful guest session; it cannot yield a false overall success. The launcher also reports `window_manager_died_during_capture` if Openbox exits unexpectedly during the NeXium screenshot/input attempt.
4. All existing runtime evidence uploads and conservative NeXium frame, host log and shutdown checks remain in force.

## Verification

Extended `tests/test_nexium_xvfb_session.py` to eight synthetic process-level cases, including a mock Openbox ignoring TERM, and a WM terminating during a guest session. Locally **8/8 passed**; `bash -n` succeeded. Tested launcher and test Git blob SHA-1s: `8adcdc80e2f980527e1e8eb35853912a9c25d546`, `aed7278a67488bd8ce22321a258872740f10f490`.

## Still unverified

No new NeXium head result was available at authoring: Stage29 NRO/GCC/Clang jobs were queued. The confirmed earlier ROM-free tactics screenshot does not establish stable emulator shutdown or keyboard/gamepad input. Actual Sega Saturn first mission, authentic map geometry and licensed game assets remain outside this prototype and no original resources are committed.

