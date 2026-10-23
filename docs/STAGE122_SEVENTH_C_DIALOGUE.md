# Stage122 — guarded seventh-C gate after Merchant/Ash dialogue

## Verified starting point

Stage121's private pair completed two original-disc cold boots through 72,000 frames. The exact in-repository Stage121 auditor passed: 600 checkpoint PNGs and 602 ordered SH2/video samples per boot; all 499 checkpoints before the sixth C at frame 60,000 matched. The first visual divergence was frame 60,120, and by 61,200 the intervention reached an outdoor scene with the dialogue “Merchant: Ash!”. That same dialogue remained at frames 66,000 and 72,000. The control still showed “...Ash... ...Ash!!!” at frame 72,000. CD/FAD event counts were 45,215 in both branches and the logs were identical.

This is a confirmed scene transition, not a controllable tactical battle.

## Stage122 public source scope

- Compose the pinned Stage121 source patch first, then add an optional seventh C at frame **72,000**, released at **72,006**.
- Extend only the bounded private capture cap to **84,000** frames.
- Require the sixth C to be enabled in both runs; only `VH_SATURN_CONFIRM7_ENABLED=0/1` may differ between the paired cold boots.
- Fail closed on missing/empty/malformed flags, invalid frame bounds, duplicate instrumentation, incorrect active-low pad state or diagnostic write failure.
- Preserve the inherited C68K, CD, video and SH2 instrumentation.
- Run GCC/Clang public runner builds and synthetic-only auditor tests. Public CI must never use original disc media.

## Future private Stage122 gate

The private auditor requires two fresh 84,000-frame cold boots, each with **700 checkpoint PNGs** and **702 ordered video/SH2 samples**. It compares all **599** checkpoints before frame 72,000 and requires reproducible framebuffer divergence no later than frame **73,200**. It also validates controller receipts, exact output sets, frame geometry, diagnostic sequences and unchanged pinned media/runner fingerprints.

Only counts, booleans and frame numbers may be exported. Never commit or upload original BIN/CUE, screenshots, extracted resources, raw FAD logs, local paths or frame hashes.

A passing integrity gate does not prove player control. The first battle requires an observed tactical turn/HUD state and a repeatable response to a separate movement/selection input. Keep authenticity Issue #11 open.

## Current state

The Stage122 patcher, synthetic-only tests, private auditor, and CI workflow are drafted in PR #77. The private seventh-C original-game pair has **not** been run yet. Keep this PR Draft until the exact-head public CI is green and the private pair and visual review are complete.
