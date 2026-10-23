# Stage119 — controlled fifth C press in the prologue

## Stage118 result

The private Stage118 pair completed 48,000 frames. Both runs matched at all 349 checkpoints before the fourth C at frame 42,000, then first diverged at frame 42,120. By frame 43,200, the fourth-C intervention displayed “Th...these rays... What's happening?” while the triple-C control remained on “Oh...that sparkle... This must be it!”

This verifies another prologue dialogue transition, not a controllable tactical battle. The scripted 3D scene and dialogue remain visible through frame 48,000.

## Controlled comparison

Stage119 tests one additional C pulse at frame 46,000, released at frame 46,006. Both cold boots use the same preceding schedule:

- START at frame 12,060, released at 12,066.
- First C at frame 12,240, released at 12,246.
- Second C at frame 31,200, released at 31,206.
- Third C at frame 36,000, released at 36,006.
- Fourth C at frame 42,000, released at 42,006.

The fourth-C baseline and fifth-C intervention receive the same fifth-C frame schedule and environment keys; only VH_SATURN_CONFIRM5_ENABLED differs (0 versus 1). The private output directories must be siblings with equal-length absolute paths so HOME, TMPDIR and capture-path environment values have matching shape.

## Audit gates

- Both cold boots must complete 48,000 frames with 400 valid sequential PNG checkpoints and 402 ordered video/SH2 samples per run.
- The media and public runner fingerprints must match pinned values before and after both processes.
- Every checkpoint before frame 46,000 must be byte-identical between the fourth-C baseline and fifth-C intervention (383 checkpoints).
- The auditor must observe a framebuffer divergence by frame 47,200. No pre-input divergence or missing controller receipt is accepted.
- A changed framebuffer is not proof of battle control. Inspect the private late frames for dialogue progression, tactical HUD/turn state and a player-input response.

## Public CI

The workflow builds the genuine public Yabause C68K software runner with GCC and Clang from pinned source, runs synthetic-only Stage119 and inherited regression tests, performs a disc-free CLI/fail-closed 48,000-frame smoke check, and uploads only the public GPL executable. It must not access original BIN/CUE media or private captures.

## Private execution

Download a runner from the successful exact-head Stage119 Actions job and use the SHA-256 printed by that same job. Create two fresh empty 0700 directories outside the checkout with sibling paths of equal length.

    python3 -m tools.saturn_private_prologue_continue_fifth_c \
      --cue "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1).cue" \
      --track1 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 1).bin" \
      --track2 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 2).bin" \
      --executable "/private/yabause" \
      --expected-runner-sha256 "LOWERCASE_SHA256_FROM_EXACT_HEAD_CI" \
      --fourth-c "/private/runs/fourth-c" \
      --fifth-c "/private/runs/fifth-c" \
      --timeout 7200

The report exports only booleans, counts and frame numbers. Never commit or upload original BIN/CUE files, private screenshots, raw FAD logs, extracted game resources, local paths or frame hashes. Keep authenticity Issue #11 open until the first controllable tactical battle is independently verified.
