# Stage119 — controlled fifth C press in the prologue

## Stage118 result

The private Stage118 pair completed 48,000 frames per cold boot using the exact-head Clang runner. The Stage118 comparison found all 349 checkpoints before frame 42,000 byte-identical. First divergence was frame 42,120. At frame 42,480 the fourth-C run showed “Th...these rays... What's happening?” with a new ray/ring animation, while the control remained on “Oh...that sparkle... This must be it!”. The new line remained at frame 48,000.

This confirms a fourth-C-driven dialogue/room transition, not a controllable tactical battle. The next experiment tests whether another C press advances the new line.

## Controlled comparison

Stage119 extends the exact pinned Stage118 runner to 60,000 frames and tests a fifth C pulse at frame 48,000, released at frame 48,006.

Both cold boots use the same preceding schedule:
- START at frame 12,060, released at 12,066.
- First C at frame 12,240, released at 12,246.
- Second C at frame 31,200, released at 31,206.
- Third C at frame 36,000, released at 36,006.
- Fourth C at frame 42,000, released at 42,006.

The four-C baseline and fifth-C intervention receive the same fifth-C frame schedule and identical environment keys; only VH_SATURN_CONFIRM5_ENABLED differs (0 versus 1). Output directories must be siblings with equal-length absolute paths so HOME, TMPDIR, and capture-path environment values have matching shape.

## Audit gates

- Both cold boots must complete 60,000 frames with 500 valid sequential PNG checkpoints and 502 ordered video/SH2 diagnostic samples per run.
- Original media and the public runner fingerprints must match the pinned values before and after both processes.
- All 399 checkpoints before frame 48,000 must be byte-identical between the four-C control and fifth-C intervention.
- The auditor must observe a framebuffer divergence by frame 49,200. No pre-input divergence or missing controller receipt is accepted.
- A changed framebuffer is not proof of battle control. Inspect the private late frames for dialogue progression, tactical HUD/turn state and a player-input response.

## Reproducible runner artifacts

The exact Stage119 GCC/Clang workflow builds the pinned public Yabause source and uploads only the public GPL emulator executable. After the exact-head run passes, record the executable SHA-256 printed by each build job here; do not confuse it with the GitHub artifact ZIP digest. Independently hash the downloaded runner before private execution.

## Private execution

Download the GCC or Clang executable from a successful exact-head Stage119 Actions run. Create two fresh empty 0700 directories outside the checkout with sibling paths of equal length, such as /private/runs/fourth and /private/runs/fifth_.

    python3 -m tools.saturn_private_prologue_continue_fifth_c \
      --cue "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1).cue" \
      --track1 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 1).bin" \
      --track2 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 2).bin" \
      --executable "/private/yabause" \
      --expected-runner-sha256 "LOWERCASE_SHA256_FROM_EXACT_HEAD_CI" \
      --fourth-c "/private/runs/fourth" \
      --fifth-c "/private/runs/fifth_" \
      --timeout 7200

The report exports only booleans, counts and frame numbers. Never commit or upload original BIN/CUE files, private screenshots, raw FAD logs, extracted game resources, local paths or frame hashes. Keep authenticity Issue #11 open until the first controllable tactical battle is independently verified.
