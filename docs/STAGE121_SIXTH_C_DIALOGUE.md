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
