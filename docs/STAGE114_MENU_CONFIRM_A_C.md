# Stage114 — verify a real A/C menu-confirm input

## Motivation

The Stage113 private three-run experiment exposed an attract-mode trap: the no-input, first-START-only and dual-START runs all eventually entered a battle-demo sequence. The title displayed “Press START Button”, the idle path displayed “Now Loading”, and the later battle scene appeared even without START. This is not evidence that New Game or the first mission was selected.

The next experiment sends a native Saturn A or C press/release after START has opened the menu. The runner uses the pinned Yabause peripheral API, where A and C have distinct active-low bits; it records numeric-only local receipts for the exact button, frame and bit transition.

## Controlled pair

Use the same Stage114 executable and original English v1.1 disc for two independent cold boots:

1. **First-START-only control:** START at frame 12060, then no more input.
2. **Confirm intervention:** START at frame 12060, then either A or C at frame 12240, released at frame 12246.

Only one confirm button is tested per run. The runner rejects an unknown button, missing environment partner, confirm without the first START, a confirm pulse too close to START, or a run that also configures the Stage112 second START. Both runs are capped at 24,000 frames. The original media and executable are fingerprinted before and after each process; all captures remain in separate private 0700 directories outside the checkout.

## Audit gates

- All 100 checkpoints from frame 120 through 12000 must match before START.
- The control and confirm runs must remain byte-identical through frame 12120, before the confirm pulse.
- The confirm run must diverge from the first-START-only control at one or more checkpoints between 12360 and 13560. This is deliberately before the observed idle attract transition, which began around frame 13680. If there is no early divergence, the audit fails closed.
- A passing numeric audit only proves a reproducible input-associated change. Review private frames to distinguish a New Game intro/mission from the attract demo; do not mark the first tactical battle verified based on a loading screen or battle-like image alone.

## Private command

Download the GCC executable from the successful exact-head Stage114 workflow and use the SHA-256 printed by that same job. Create two empty 0700 output directories. Test A first; if it does not produce an early, visually meaningful transition, repeat the controlled pair with C using fresh directories.

    python3 -m tools.saturn_private_original_confirm_sequence \
      --cue "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1).cue" \
      --track1 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 1).bin" \
      --track2 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 2).bin" \
      --executable "/private/yabause" \
      --expected-runner-sha256 "LOWERCASE_SHA256_FROM_EXACT_HEAD_CI" \
      --first-only "/private/runs/first-start-only" \
      --confirm "/private/runs/start-plus-confirm-a" \
      --confirm-button A \
      --timeout 7200

The report exports only booleans, counts and frame numbers. Never commit or upload original BIN/CUE files, private screenshots, raw FAD logs, extracted game resources, local paths or frame hashes. Keep Issue #11 open until the actual New Game path and first tactical mission are visually and structurally verified.
