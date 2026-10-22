# Stage116 — controlled second C press in the prologue

## Observation motivating this stage

Stage115's private START+C run completed 48,000 frames with all integrity checks passing: each run produced the exact 408-file output set, 400 valid PNG checkpoints and 402 ordered video/SH2 samples; source media and runner hashes remained pinned. The C run reached Magnus's “Ah... a hidden room.” dialogue by frame 26400, and the same line remained through frame 48000. This strongly suggests the prologue is waiting for another confirm input. The first controllable battle is still not verified.

## Controlled comparison

Use the same Stage116 GCC executable and original English v1.1 media for two separate cold boots. Both runs press START at frame 12060 and C at frame 12240, released at 12246.

- **Single-C control:** no later button input.
- **Double-C test:** one additional C press at frame 31200, released at frame 31206.

Both runs receive the same second-C frame schedule (31200); the control sets its enable flag to 0 and the intervention sets it to 1. The input branch is evaluated at the scheduled frame, so the environment-variable presence itself is not the intervention.

A preliminary private pair failed the strict pre-input equality gate at three early FMV checkpoints (6240, 9720 and 9960). That pair is not accepted as causal evidence. The cause of those early video differences is not yet established; the runner and harness have now been hardened so both processes parse the same scheduled-frame environment and differ only in the one-character enable flag before frame 31200.

Both runs stop at frame 48000. The auditor validates 400 sequential PNG checkpoints and 402 ordered video/SH2 diagnostic samples per run, active-low pad receipts, exact output file sets, private permissions, frame stats, numeric-only CD/FAD logs, and unchanged source/runner identities. It requires the two runs to match at every checkpoint before the second C pulse and records whether the second pulse produces a post-frame-31200 framebuffer divergence by frame 36000.

The private visual review must compare the dialogue at frames 30000/31080 and 32400/33600. A changed framebuffer is not by itself proof that the dialogue advanced; inspect the text and scene. Do not claim the first controllable tactical battle until the tactical HUD/turn state is active and player input is observed to change selection or movement.

## Private execution

Download the GCC or Clang executable from a successful exact-head Stage116 Actions run and use the SHA-256 printed by that same job. Create two empty 0700 directories. Keep the original BIN/CUE files, outputs and captures outside the Git checkout.

    python3 -m tools.saturn_private_prologue_continue \
      --cue "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1).cue" \
      --track1 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 1).bin" \
      --track2 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 2).bin" \
      --executable "/private/yabause" \
      --expected-runner-sha256 "LOWERCASE_SHA256_FROM_EXACT_HEAD_CI" \
      --single-c "/private/runs/single-c-48k" \
      --double-c "/private/runs/double-c-48k" \
      --timeout 7200

The report exports only booleans, counts and frame numbers. Never commit or upload original BIN/CUE files, private screenshots, raw FAD logs, extracted game resources, local paths or frame hashes. Keep authenticity Issue #11 open.
