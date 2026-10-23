# Stage121 — guarded sixth-C source gate after verified Stage119

## Original-game starting point

Stage119's private fifth-C experiment (two complete 60,000-frame cold boots, exact in-repo integrity auditor passed) showed a post-input framebuffer transition at frame **48,120**. At frame 49,200 the intervention shows a pillar of light, and by frame 54,000 and through frame 60,000 it displays **"...Ash... ...Ash!!!"**. The four-C control still shows the prior ray dialogue. This establishes dialogue/scene progression, **not** an actively controllable tactical battle. The source and evidence remain private.

## Stage121 public-code scope

This Stage121 draft introduces **source instrumentation and synthetic regression checks only**. It does **not yet** claim a private original-disc sixth-C experiment.

- Compose the pinned Stage119 fifth-confirm Yabause source patch first. Add an optional sixth C with press at frame **60,000** and release at **60,006**.
- Increase only the bounded private guest execution cap from 60,000 to **72,000** frames; preserve existing C68K/CD/video/SH2 components.
- Require the already scheduled fifth C to be enabled in both paired runs.
- Parse identical sixth input frame and environment keys in both; the only difference for a later private comparison must be `VH_SATURN_CONFIRM6_ENABLED=0` versus `1`.
- Reject absent, empty, malformed, too-early or out-of-bound sixth-C parameters, duplicate instrumentation and changed source anchors.
- Preserve native active-low C press/release receipts; reject mismatched state and log write failures.

## Future private Stage121 audit gate (not yet implemented)

For two complete 72,000-frame cold boots, the next private auditor must require:

1. Fresh, private, equal-length sibling paths and pinned original media/public runner fingerprints before and after each run.
2. **600 checkpoint PNGs** and **602 ordered video/SH2 diagnostic samples** per boot, with exact file set/geometry verification.
3. Identical initial images and **499 checkpoint PNGs** before frame 60,000.
4. Exact native controller events and active-low state receipts for the sixth-C pulse.
5. Reproducible framebuffer divergence no later than frame 61,200, followed by private visual inspection.
6. No public export of original BIN/CUE, screenshots, CD/FAD logs, extracted assets, local paths or frame hashes.

Passing a numerical equality/divergence gate would still **not** establish player control. First battle requires independently observed active tactical turn/HUD state and a repeatable response to separate player movement/selection input. Keep Issue #11 open.

## Current evidence boundary

The Stage121 source patch and ROM-free tests have been created. A corresponding private 72,000-frame pair, full Stage121 private auditor and original gameplay interpretation have **not** been completed. Keep this PR Draft and do not merge it solely on a green pinned-source build.

## Private Stage121 pair completed (23 October 2026)

The exact Stage121 Clang runner from [public CI run #39955365015](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39955365015), artifact [12502522017](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39955365015/artifacts/12502522017), was used for two private original-disc cold boots. Its executable SHA-256 matched the successful Clang build log. The exact repository auditor `audit_private_prologue_continue_sixth_c` was then run against the two private output folders and passed. A separate local cross-check also passed. No original media, screenshots, FAD traces, local paths or frame hashes are published.

- Both boots completed **72,000 frames** with **600 PNG checkpoints** and **602 ordered samples per SH2/video log**.
- All **499/499** checkpoints strictly before the sixth-C input at frame 60,000 matched byte-for-byte.
- The active-low controller receipts validated the C press at frame **60,000** and release at **60,006**.
- First post-input framebuffer divergence: **frame 60,120**; the final frame at 72,000 still differed.
- Canonical CD/FAD event counts were **45,215 in both runs** and the numeric logs were identical. This experiment did not establish a CD-read-count change.
- The original Track 1, Track 2, CUE and Stage121 executable fingerprints were unchanged before and after the pair.

Private visual review: at frame 60,120 the intervention shows a transition to black while the control remains on the prior "...Ash... ...Ash!!!" dialogue. By frame 61,200 the intervention has entered an outdoor scene with the dialogue **"Merchant: Ash!"**. The same scene/dialogue remains at frames 66,000 and 72,000, while the control still shows the prior dialogue at frame 72,000. This confirms sixth-C-driven scene progression.

**Conclusion:** Stage121 verifies another real prologue transition, but does not verify a controllable tactical battle. No tactical turn/HUD state or separate movement/selection response has been observed. Keep `first_battle_or_player_control_verified` false and authenticity Issue #11 open.

## Stage122 next experiment

The Merchant/Ash dialogue persists through frame 72,000, suggesting the next bounded experiment should test a **seventh C press at frame 72,000**, release at 72,006, and capture through 84,000. Both cold boots must keep the first six C pulses identical; only the seventh-C enable flag may differ. Reuse the exact-head source and media fingerprints, 700 checkpoint/702-sample integrity checks, and strict privacy boundary. Do not claim battle entry without separate visual and player-input evidence.
