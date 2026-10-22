# Stage113 — isolate the second START pulse with three private runs

## Why a third run is required

Stage112's no-input control versus dual-START intervention proves the title-to-menu response, but it cannot isolate the second START: the intervention has already diverged from the no-input control after the first pulse. Stage113 adds a first-START-only control so the second pulse can be evaluated independently.

## Three cold boots

Run the same pinned Stage113 GCC executable and the same Stage02-verified English v1.1 Track 1, Track 2 and CUE in three separate, empty 0700 output directories:

1. **No-input control:** no START environment variables.
2. **First-START-only control:** VH_SATURN_START_AT_FRAME=12060; no second pulse.
3. **Dual-START intervention:** first pulse at 12060 and second pulse at VH_SATURN_START_AT_FRAME2=12240.

Every run is bounded to 24,000 emulated frames. The private auditor verifies the runner SHA-256 against the exact successful public GCC workflow artifact, pins all original media before and after each process, checks the capture gate and numeric pad-bit receipts, requires all 200 sequential checkpoint PNGs and consistent frame statistics, and rejects unexpected or non-private output files.

## Evidence gates

- All three runs must have identical checkpoint images from frame 120 through 12000, before the first START pulse.
- The first-START-only and dual-START runs must remain byte-identical through frame 12120, before the second pulse.
- The no-input and first-START-only runs must visibly diverge at checkpoints 12120 and 13200, consistent with the verified title-to-menu transition.
- The first-START-only and dual-START runs are compared at every one of the 98 checkpoints from frame 12360 through 24000. At least one must differ; otherwise the audit fails closed and does not claim the second pulse had an observable effect. This full sweep also reports the earliest measurable divergence.
- A framebuffer difference is not by itself proof of a tactical battle. Inspect the protected local images and correlate any scene transition with numeric CD-read evidence before updating authenticity Issue #11.

## First private three-run observation (local only)

The original English v1.1 disc was run in three isolated 24,000-frame sessions using the exact GCC artifact whose SHA-256 was printed by the successful Stage113 CI job. That executable is byte-identical to the Stage112 artifact. Track 1, Track 2, CUE and executable hashes matched their pins before and after the runs. Each session produced the exact 208-file output set, 200 valid sequential checkpoint PNGs, 202 video/SH2 samples, matching pad receipts, a closed capture gate and private file permissions.

The no-input run remained on the title's “Press START Button” screen until the attract sequence began loading at frame 13560; a battle-demo scene was visible by frame 13800. The first-START-only run showed the menu, began loading at frame 13680 and reached a battle-demo scene shortly afterward. The dual-START run began loading at frame 13800 and also reached the demo. The three runs were identical through frame 12000; first-only and dual-START remained identical through frame 12120. Their first measurable post-second-pulse framebuffer divergence was frame 13680.

**Interpretation:** the long-window battle image is an attract/demo sequence, not proof of a new game or the first mission. START inputs appear to delay the attract transition. The next experiment must send an actual menu-confirm button (A or C) after the title-to-menu START pulse and compare it against a same-runner first-START-only control. Issue #11 remains open.

## Private execution

Download the GCC executable artifact from the successful exact-head Stage113 Actions run. Independently verify its SHA-256 using the value printed by that same workflow job. Restore the original media from the private archive parts, preserve the exact filenames referenced by the CUE, and keep all media and outputs outside the Git checkout.

Example command (replace the example paths with the local protected paths):

    python3 -m tools.saturn_private_original_start_triple \
      --cue "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1).cue" \
      --track1 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 1).bin" \
      --track2 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 2).bin" \
      --executable "/private/yabause" \
      --expected-runner-sha256 "LOWERCASE_SHA256_FROM_EXACT_HEAD_CI" \
      --no-input "/private/runs/no-input" \
      --first-only "/private/runs/first-start-only" \
      --dual-start "/private/runs/dual-start" \
      --timeout 7200

The report intentionally exports only booleans, counts and frame numbers. Never commit or upload original BIN/CUE files, private screenshots, raw FAD logs, extracted game resources, local paths or frame hashes. Keep Issue #11 open until the authentic tactical map/battlefield and loader relationship are independently reviewed.
