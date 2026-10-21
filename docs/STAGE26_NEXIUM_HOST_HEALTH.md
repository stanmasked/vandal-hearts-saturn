# Stage 26 — Separate framebuffer success from NeXium host stability

## Real captured evidence

The genuine ROM-free Nintendo Switch NRO successfully booted and rendered an actual 1280x720 tactics board with two allied blue units and two red enemy units in NeXium under GitHub Actions #39396848917 (Stage 22). The visual classifier counted two of each and manual review independently confirmed the screenshot. Screen SHA-256: `bc28bc9b0316dc60f6faab5bf12883272c0a8a5948f2f164ec97e92f13df683d`.

**However**, the accompanying NeXium GUI host log contains a Rust panic (`panicked at`) and X11 connection I/O error (`Connection(IoError...)`). The timing of those errors relative to capture is not known: they might have occurred during emulator shutdown or indicate a more serious runtime stability bug. The Stage 22 job previously passed because it only required a screenshot and unit colors. That success is good proof of a visible *frame*, not proof of stable emulator operation.

## Stage 26 changes

- New read-only `tools/nexium_log_health.py` classifies host log errors (Rust panic, X11 connection failure, SIGSEGV, Vulkan device loss, and fatal markers) and treats ordinary ALSA missing-audio warnings separately.
- CI `run-in-nexium` adds an `if: always()` host-log gate before the existing unconditional evidence upload. Fatal host errors now fail the runtime job **even if a framebuffer screenshot passed**.
- Count-only JSON `runtime-evidence/emulator-log-health.json` is published with the existing screenshot/host log archive. Large logs are rejected. No source files or original game assets are exported.
- New `tests/test_nexium_log_health.py` has seven synthetic-only scenarios. **7/7 local tests pass**.

## Independent rerun on real Stage 22 host log

`known_fatal_error_count=2`, categories `rust_panic` and `x11_connection_failure`; `audio_device_warning_present=true`; `no_known_fatal_host_errors=false`. That is a diagnostic **finding**, not a repair. It does not invalidate the already witnessed synthetic game frame, but prevents declaring stable NeXium runtime.

## Next gates

Check whether NeXium's panic happened before or during Xvfb/GUI teardown, improve orderly shutdown if necessary, then capture a full guest-input sequence. Also continue separate authentication of the first genuine Sega Saturn mission. No copyrighted disc data is committed.
