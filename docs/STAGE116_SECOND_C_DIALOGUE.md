# Stage116 — controlled second C press in the prologue

## Observation motivating this stage

Stage115's private START+C run reached the Magnus dialogue “Ah... a hidden room.” by frame 26400. The same line remained on screen through at least frame 32400 while character animation continued. This suggests the dialogue is waiting for player confirmation. Stage115's one-C 48,000-frame pair is still being audited; it does not claim that the first battle is playable.

## Controlled comparison

Use the same Stage116 GCC executable and original English v1.1 media for two separate cold boots. Both runs press START at frame 12060 and C at frame 12240, released at 12246.

- **Single-C control:** no later button input.
- **Double-C test:** one additional C press at frame 31200, released at frame 31206.

Both runs stop at frame 48000. The auditor validates 400 sequential PNG checkpoints and 402 ordered video/SH2 diagnostic samples per run, active-low pad receipts, exact output file sets, private permissions, frame stats, numeric-only CD/FAD logs, and unchanged source/runner identities. It requires the two runs to match before the first C press and records whether the second pulse produces a post-frame-31200 framebuffer divergence by frame 36000.

The private visual review must compare the dialogue at frames 30000/31080 and 32400/33600. A changed framebuffer is not by itself proof that the dialogue advanced; inspect the text and scene. Do not claim the first controllable tactical battle until the tactical HUD/turn state is active and player input is observed to change selection or movement.

## Private execution

Download the GCC executable from the successful exact-head Stage116 Actions run and use the SHA-256 printed by that same job. Create two empty 0700 directories. Keep the original BIN/CUE files, outputs and captures outside the Git checkout.

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
