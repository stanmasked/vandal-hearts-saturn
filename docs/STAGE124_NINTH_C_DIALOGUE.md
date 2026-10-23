# Stage124 — guarded ninth-C gate after Merchant warning

## Verified starting point

Stage123 completed a private paired original-disc experiment using the exact public Clang runner artifact from CI. Both cold boots reached 96,000 frames; all 800 checkpoint PNGs and 802 ordered SH2/video samples per boot passed the exact repository auditor. All 699 checkpoints strictly before the eighth C at frame 84,000 matched. The first post-input framebuffer divergence was frame 84,120.

At frame 85,200, the intervention advanced the lower dialogue from “Merchant: Ash!” to “Merchant: Well you better get up. We've got some trouble.” The control stayed on “Merchant: Ash!” through frame 96,000. Both runs recorded 54,103 canonical CD/FAD events and identical numeric logs. This confirms dialogue progression, not tactical battle entry.

## Stage124 public source scope

- Compose the pinned Stage123 source patch, then add an optional ninth C at frame **96,000**, released at **96,006**.
- Extend only the bounded private capture cap to **108,000** frames.
- Require the eighth C to be enabled in both runs; only `VH_SATURN_CONFIRM9_ENABLED=0/1` may differ.
- Fail closed on missing/empty/malformed flags, invalid bounds, duplicate instrumentation, incorrect active-low pad state or diagnostic write failure.
- Preserve inherited C68K, CD, video and SH2 instrumentation.
- Run GCC/Clang public runner builds and synthetic-only tests. Public CI must never use original disc media.

## Future private Stage124 gate

The private auditor requires two fresh 108,000-frame cold boots, each with **900 checkpoint PNGs** and **902 ordered video/SH2 samples**. All **799** checkpoints strictly before frame 96,000 must match; the intervention must produce a reproducible framebuffer divergence by frame **97,200**. The audit also validates controller receipts, exact output sets, frame geometry, diagnostic sequences, and unchanged pinned media/runner fingerprints.

Only counts, booleans and frame numbers may be exported. Never commit or upload original BIN/CUE, screenshots, extracted resources, raw FAD logs, local paths or frame hashes.

A passing integrity gate does not prove player control. The first battle requires an observed tactical turn/HUD state and a repeatable response to a separate movement/selection input. Keep authenticity Issue #11 open.

## Current state

The Stage124 patcher, synthetic-only tests, private auditor, and CI workflow are drafted in PR #80. The Stage124 original-game pair has **not** been run yet. Keep this PR Draft until exact-head public CI passes and the private pair plus visual review are complete.
