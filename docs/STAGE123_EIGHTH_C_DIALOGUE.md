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

## Private Stage123 pair completed (23 October 2026)

Used the exact Stage123 Clang runner from [public CI run #39964675108](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39964675108), artifact [12506383710](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39964675108/artifacts/12506383710), SHA-256 `42be39781e5050a51508cd1d85c9d386bff0353df4fc178e4a7f4b1bb4de5fb2`. The exact Stage123 private auditor completed successfully on two cold boots of the original disc.

- Both runs completed **96,000 frames**, with **800 checkpoint PNGs** and **802 ordered SH2/video samples** per run.
- All **699/699** checkpoints strictly before the eighth C at frame **84,000** matched byte-for-byte.
- Active-low receipts verified press at **84,000** and release at **84,006**.
- First framebuffer divergence: **frame 84,120**; the intervention still differs at frame 96,000.
- Both runs recorded **54,103 canonical CD/FAD events** with identical numeric logs.
- Private visual review at frame **85,200**: the intervention's lower dialogue advances to “Merchant: Well you better get up. We've got some trouble.” The control still shows “Merchant: Ash!”. By frame 96,000 the intervention retains the new Merchant dialogue, while the control remains on “Ash!”. The upper “Man Called Ash” dialogue is unchanged.
- Original media and public runner fingerprints remained unchanged before and after both runs. No original media, screenshots, raw logs, local paths or frame hashes were exported.

This confirms eighth-C-driven **dialogue progression**, not tactical battle entry or player control. Keep authenticity Issue #11 open and `first_battle_or_player_control_verified` false.

The source gate passed on the code-equivalent revision used to build the private runner, with both GCC and Clang. The latest workflow revision additionally runs Stage122 inherited regressions; its exact-head GitHub Actions checks are still queued. Keep PR #79 Draft until those checks and the stacked PR chain are ready.

## Stage124 next experiment

Use Stage123 as the exact parent. Keep the first eight C pulses enabled in both cold boots and test a **ninth C at frame 96,000**, released at **96,006**, through a **108,000-frame** cap. Only the ninth-C enable flag may differ. Require **900 checkpoint PNGs** and **902 ordered diagnostic samples** per boot; all **799 checkpoints** strictly before frame 96,000 must match. Require reproducible framebuffer divergence by frame **97,200**. Keep original media, images, raw logs and frame hashes private.

The current scene is still a conversation. Do not claim battle entry without a visible tactical turn/HUD state and a separate, repeatable movement or selection response.
