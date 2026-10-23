# Stage123 — guarded eighth-C gate after Ash dialogue

## Verified starting point

Stage122 completed a private paired original-disc experiment using the exact Stage122 Clang runner from public CI. Both cold boots reached 84,000 frames; all 700 checkpoint PNGs and 702 ordered SH2/video samples per boot passed the exact repository auditor. All 599 checkpoints strictly before the seventh C at frame 72,000 matched. The first post-input framebuffer divergence was frame 72,120.

At frame 72,120, the intervention added the top dialogue “Man Called Ash: Huh...”; by frame 73,200 it showed “Oh, sorry. I was just thinking...”. The same dialogue remained at frame 84,000, while the control stayed on “Merchant: Ash!”. Both branches recorded 49,659 canonical CD/FAD events and identical numeric logs. This is confirmed dialogue progression, not a controllable tactical battle.

## Stage123 public source scope

- Compose the pinned Stage122 source patch, then add an optional eighth C at frame **84,000**, released at **84,006**.
- Extend only the bounded private capture cap to **96,000** frames.
- Require the seventh C to be enabled in both runs; only `VH_SATURN_CONFIRM8_ENABLED=0/1` may differ.
- Fail closed on missing/empty/malformed flags, invalid bounds, duplicate instrumentation, incorrect active-low pad state or diagnostic write failure.
- Preserve inherited C68K, CD, video and SH2 instrumentation.
- Run GCC/Clang public runner builds and synthetic-only tests. Public CI must never use original disc media.

## Future private Stage123 gate

The private auditor requires two fresh 96,000-frame cold boots, each with **800 checkpoint PNGs** and **802 ordered video/SH2 samples**. All **699** checkpoints strictly before frame 84,000 must match; the intervention must produce a reproducible framebuffer divergence by frame **85,200**. The audit also validates controller receipts, exact output sets, frame geometry, diagnostic sequences, and unchanged pinned media/runner fingerprints.

Only counts, booleans and frame numbers may be exported. Never commit or upload original BIN/CUE, screenshots, extracted resources, raw FAD logs, local paths or frame hashes.

A passing integrity gate does not prove player control. The first battle requires an observed tactical turn/HUD state and a repeatable response to a separate movement/selection input. Keep authenticity Issue #11 open.

## Current state

The Stage123 patcher, synthetic-only tests, private auditor, and CI workflow are drafted in PR #79. The Stage123 original-game pair has **not** been run yet. Keep this PR Draft until exact-head public CI passes and the private pair plus visual review are complete.
