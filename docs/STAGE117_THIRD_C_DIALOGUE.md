# Stage117 — controlled third C press in the prologue

## Stage116 result

A controlled 48,000-frame pair using the original English v1.1 disc passed strict integrity checks. The two runs matched at all 259 checkpoints before the second C at frame 31,200, then first diverged at frame 31,320. The second-C path progressed from Magnus's “Ah...a hidden room.” to “Hmm? What's that?” by frame 32,400, but the latter dialogue remained visible through frame 48,000. The first controllable tactical battle is still not verified.

## Controlled comparison

Stage117 tests one additional C pulse at frame 42,000, released at frame 42,006. The baseline and intervention both use:

- START at frame 12,060.
- Initial C at frame 12,240, released at 12,246.
- Second C at frame 31,200, released at 31,206.

The only intervention is whether the third C at frame 42,000 is enabled. Both runs receive the same third-C schedule and the same environment keys; the enable flag is 0 for the double-C baseline and 1 for the triple-C intervention. The two private output directories must be siblings with equal-length absolute paths so HOME, TMPDIR and capture-path environment values have matching shape.

## Audit gates

- Both cold boots must complete 48,000 frames with 400 valid sequential PNG checkpoints and 402 ordered video/SH2 samples per run.
- Every checkpoint before frame 42,000 must be byte-identical between the double-C and triple-C runs.
- The auditor must observe a reproducible framebuffer divergence after the third C and before or at frame 48,000. If there is no difference, the audit fails closed.
- A frame difference is not proof of battle control. Inspect the private late frames for dialogue progression, tactical HUD/turn state and a player-input response.

## Private execution

Download the GCC or Clang executable from the successful exact-head Stage117 Actions run and use the SHA-256 printed by that same job. Create two fresh empty 0700 directories outside the checkout with sibling paths of equal length.

    python3 -m tools.saturn_private_prologue_next_dialogue \
      --cue "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1).cue" \
      --track1 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 1).bin" \
      --track2 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 2).bin" \
      --executable "/private/yabause" \
      --expected-runner-sha256 "LOWERCASE_SHA256_FROM_EXACT_HEAD_CI" \
      --double-c "/private/runs/double-c" \
      --triple-c "/private/runs/triple-c" \
      --timeout 7200

The report exports only booleans, counts and frame numbers. Never commit or upload original BIN/CUE files, private screenshots, raw FAD logs, extracted game resources, local paths or frame hashes. Keep authenticity Issue #11 open until the first controllable tactical battle is independently verified.
