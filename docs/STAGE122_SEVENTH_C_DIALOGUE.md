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

The Stage122 private pair is complete and the private auditor implementation passed. Stage122 GCC/Clang source gates, host GCC/Clang tests and Switch NRO passed at the prior code head; exact-head checks after syncing the bounded NeXium dependency setup are pending. The NeXium guest framebuffer smoke has not yet supplied a successful result. Keep PR #77 Draft while the stacked chain and guest evidence remain incomplete.


## Private Stage122 pair completed (23 October 2026)

The exact Stage122 Clang runner from [public CI run #39958654436](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39958654436), artifact [12503158266](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39958654436/artifacts/12503158266), was used for two private original-disc cold boots. The runner SHA-256 was verified before execution; the Stage122 private auditor implementation passed, and media/runner fingerprints were unchanged after the pair.

- Both cold boots completed **84,000 frames**, with **700 PNG checkpoints** and **702 ordered SH2/video samples** each.
- All **599/599** checkpoints strictly before the seventh C at frame **72,000** matched byte-for-byte.
- The active-low receipts verified the seventh-C press at **72,000** and release at **72,006**.
- First framebuffer divergence: **frame 72,120**; the final frame at 84,000 still differs.
- Both runs recorded **49,659** canonical CD/FAD events, with identical numeric logs. No CD event-count change was established.
- Private visual review: the intervention adds the top dialogue “Man Called Ash: Huh...” at frame 72,120, followed by “Oh, sorry. I was just thinking...” by frame 73,200. That dialogue remains at frame 84,000; the control still shows “Merchant: Ash!”. This confirms seventh-C-driven dialogue progression, not tactical battle entry.
- No original media, screenshots, raw logs, local paths or frame hashes were committed or uploaded.

The source gate, host GCC/Clang tests, and Switch NRO build passed at the pre-documentation code head. The NeXium guest framebuffer smoke was queued separately and has not yet supplied an additional successful result.

## Stage123 next experiment

Use the Stage122 source as the exact parent, keep the first seven C pulses enabled in both cold boots, and test an **eighth C at frame 84,000**, released at **84,006**, through a **96,000-frame** cap. Only the eighth-C enable flag may differ. Require 800 checkpoint PNGs and 802 ordered diagnostic samples per boot; all 699 checkpoints strictly before frame 84,000 must match. Require a reproducible framebuffer divergence by frame 85,200 and keep original media, images, raw logs and frame hashes private.

The current visual evidence remains a conversation scene. Do not claim battle entry or player control without a separately observed tactical HUD/turn state and a repeatable movement or selection response.
