# Stage 29 — Use an actual X11 window manager for NeXium GUI shutdown

## Evidence and hypothesis

The first real Stage22 NeXium screenshot shows the ROM-free tactics board; however the Rust/winit host log reports a panic at an X11 connection error. Stage23/24 also captured frames but reached the 110-second external timeout. Stages27/28 add phase-separated logs, graceful windowclose, force-close detection and bounded optional input.

The CI graphical session previously ran **bare Xvfb with no window manager**. Under that configuration, a request to activate or gracefully close the NeXium window can be ignored or handled differently than a standards-compliant WM_DELETE_WINDOW. This is a concrete environmental weakness but NOT a proven root cause of the Rust panic.

## Stage29 implementation

- Install `openbox` and `wmctrl` in the Ubuntu 26.04 NeXium runner; keep existing Xvfb and Lavapipe software Vulkan.
- Start Openbox as an X11 window manager **inside the same Xvfb display**, verify it advertises `Name: Openbox` through `wmctrl -m`, and preserve `window-manager.log` and `window-manager-status.txt` in runtime evidence.
- Fail explicitly and save `window-manager-failure.txt` if Openbox dies or fails to register; do not fake NeXium success.
- Only after readiness execute the existing real `scripts/nexium_capture.sh` (which contains bounded input, real screenshot, WM_DELETE request, graceful/forced shutdown receipts). Its actual exit code propagates.
- Add same-branch GitHub Actions `concurrency` groups separately for Host and Switch workflows. Older queued/running revisions can be canceled when newer changes supersede them, avoiding redundant CI buildup.

## Validation

On the local Linux runtime, `xvfb-run -a` with a real Openbox process returned `Name: Openbox` from `wmctrl -m` (verified).

`tests/test_nexium_xvfb_session.py`: 6 synthetic-only tests all passed. They cover valid shell syntax, successful WM readiness and guest-invocation forwarding, guest failure propagation, missing WM, early WM termination, and malicious timing value rejection. No Sega Saturn binary or protected asset is used.

## Hard gate

This is NOT yet a fix for the existing panic. The new Actions run must demonstrate a frame, stage27 pre/post-close logs, successful non-forced exit and absence of fatal Rust/X11 errors. The optional keyboard screenshot pair remains secondary. The original Sega Saturn first mission and map semantics remain unverified and unimplemented.
