# Stage 36 — Probe X11 WM_DELETE_WINDOW before close; use Openbox EWMH request

## Observed upstream failure

Real NeXium CI #39450477582 compiled the native ROM-free Switch NRO, displayed two screenshot frames and passed all independent guest frame, 64-bit state and Right-key cursor checks. The host then exited 101 with a winit 0.30.13 panic on X11 GetGeometry (BadDrawable), after `windowclose_sent`. The complete log snapshot before the close had ALSA audio warnings only; the lifecycle auditor correctly reported `fatal_after_close_request=['rust_panic']` and no fatal-before-close categories.

## More precise experiment

`xdotool windowclose` can behave differently depending on whether the target X11 window advertises `WM_DELETE_WINDOW` in its `WM_PROTOCOLS` property. Blindly closing a winit-owned window risks destroying its drawable before its GUI code has finished using it. This is a plausible upstream close-path problem, not proven root cause.

New `scripts/nexium_x11_close.sh` takes the visible X11 numeric window ID and **first reads** `WM_PROTOCOLS` using a bounded `xprop` query. Only if `WM_DELETE_WINDOW` is advertised, it sends an EWMH `_NET_CLOSE_WINDOW` request via `wmctrl -ic` (Openbox). It does not call `xdotool windowclose` or use XKillClient. The request and protocol evidence are saved as `runtime-evidence/x11-close-status.txt` and `x11-wm-protocols.txt`. Missing protocols and failed requests are fatal, with explicit receipts.

The existing launcher still snapshots `nexium-log-before-close.log` before requesting exit, and still requires NeXium to exit **zero without forced signals**. The strict Rust fatal-log classifier and before/after lifecycle audit are unchanged: a winit panic after this experimental new method still fails. EWMH requested does not itself prove the host exit was clean.

Ubuntu CI now installs `x11-utils` explicitly, syntax-checks the new helper and sets `RUST_BACKTRACE=1` to preserve a trace should the nightly NeXium binary panic again.

## Test coverage

New `tests/test_nexium_x11_close.py`: 8 genuine subprocess-level mock-X11 tests, including valid protocol and WM route, missing protocol, X11 query failure, WM rejection/hang, invalid window ID/timeout, and Bash syntax. **8/8 locally passed**.

Existing `test_nexium_lifecycle.py` and `test_nexium_launcher_integration.py` fake X11 utilities are adjusted to cover the changed default shutdown pathway, rather than requiring an actual NeXium GUI in unit tests.

## Remaining evidence

New GitHub NRO/NeXium run is needed. On the first live run, inspect x11-wm-protocols.txt and the pre/post-close logs to determine whether NeXium advertises a supported WM_DELETE_WINDOW and whether a standards-based EWMH close changes the panic. Physical Switch gamepad and authentic Sega Saturn first mission remain untested/unfinished; original game assets remain private.
