# Stage 38 — Three independent real NeXium reliability trials

## Goal

Previous ROM-free NRO runs successfully built, displayed synthetic battle units, decoded the 64-bit guest state fingerprint and closed NeXium without panic. One earlier run dispatched Right but showed no visible cursor motion. This stage measures repeatability instead of extrapolating from one green job.

## What changes

- After the original native NRO build and existing mandatory framebuffer/input/host-closure gates, launch **two additional** independent NeXium processes, each with its own `xvfb-run` display, Openbox, startup, screenshot pair, bounded Right input and WM_DELETE shutdown. The **same exact NRO and downloaded nightly emulator binary** are reused; no second compilation or download.
- `scripts/nexium_repeat_trials.sh` preserves original validated trial as `trial-01`, then runs `trial-02` and `trial-03` in isolated temporary working directories. It records exact launcher exit status and preserves full per-run evidence even after a failed trial. Both additional processes have a 110-second timeout, and failures cannot be dropped.
- `tools/nexium_repeat_audit.py` independently rechecks each trial using existing actual production visual/pixel and log auditors: two-blue/two-red frame, 64-bit checksum and Right response in **both** images, clean host log, clean before/after-close lifecycle, reaped Openbox and launcher exit code zero.
- A strict JSON `runtime-evidence/repeat-audit.json` captures **3/3 or lower** plus first-attempt successes and genuinely screenshot-verified fallback recoveries. The whole job fails if any of three trials fails, and the original two-frame guest and strict X11 lifecycle gates remain mandatory.

## Host unit tests

`tests/test_nexium_repeat_audit.py` covers 7 cases: all-pass, one failure, retry accounting, missing evidence, malformed launcher status, explicit timeout/nonzero status, and enumeration of distinct independent trials. The Bash wrapper is also syntax-checked. No original Saturn game files or graphics are required.

## Remaining limits

Three launches constitute a small empirical sample, not a guarantee of stability; only X11 keyboard response is measured, **not physical Nintendo Switch Joy-Con or Pro Controller**. Genuine Sega Saturn first-battle terrain, characters and map rules remain unimplemented; all original licensed material remains private.
