# Stage118 — controlled fourth C press in the prologue

## Stage117 result

The private Stage117 pair completed 48,000 frames. The double-C control and triple-C intervention matched at all 299 checkpoints before the third C at frame 36,000, then first diverged at frame 36,120. At frame 37,200 the intervention showed “Oh...that sparkle... This must be it!” in the 3D room while the control still showed “Hmm? What's that?”

This establishes a reproducible third-C-driven dialogue/room transition. It does not establish a controllable tactical battle; the new dialogue remains visible and no active turn HUD/player-input response has been verified.

## Controlled comparison

Stage118 tests one additional C pulse at frame 42,000, released at frame 42,006. Both cold boots use the same preceding schedule:

- START at frame 12,060, released at 12,066.
- First C at frame 12,240, released at 12,246.
- Second C at frame 31,200, released at 31,206.
- Third C at frame 36,000, released at 36,006.

The triple-C baseline and fourth-C intervention receive the same fourth-C frame schedule and the same environment keys; only VH_SATURN_CONFIRM4_ENABLED differs (0 versus 1). The private output directories must be siblings with equal-length absolute paths so HOME, TMPDIR and capture-path environment values have matching shape.

## Audit gates

- Both cold boots must complete 48,000 frames with 400 valid sequential PNG checkpoints and 402 ordered video/SH2 diagnostic samples per run.
- The media and public runner fingerprints must match the pinned values before and after both processes.
- Every checkpoint before frame 42,000 must be byte-identical between the triple-C and fourth-C runs (349 checkpoints).
- The auditor must observe a framebuffer divergence by frame 43,200. No pre-input divergence or missing controller receipt is accepted.
- A changed framebuffer is not proof of battle control. Inspect the private late frames for dialogue progression, tactical HUD/turn state and a player-input response.

## Reproducible runner artifacts

The exact Stage118 source revision `aa3dc4f224a9537a73610b6f9d081e182042e8f9` passed the public-only GCC/Clang runner workflow [#39874852213](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39874852213). The artifact ZIP digests shown by GitHub are distinct from the executable SHA-256 values printed by each build job:

- Clang artifact `stage118-public-linked-yabause-clang` (artifact ID `12468631757`): executable SHA-256 `b4a682579d1da7804d4fe0e7ff8864a50aa30dd715e15d7a7265febd89f1bdf5`.
- GCC artifact `stage118-public-linked-yabause-gcc` (artifact ID `12468493678`): executable SHA-256 `ba061492d4773a0bf0893ee38f93498d080c8d8cfdef3a2c4be3cd9f81a09669`.

Before a private run, independently hash the downloaded executable and compare it with the selected compiler's value above. Do not use the artifact ZIP digest as the executable digest.

## Private execution

Download the GCC or Clang executable from the successful exact-head Stage118 Actions run and use the SHA-256 printed by that same job. Create two fresh empty 0700 directories outside the checkout with sibling paths of equal length.

    python3 -m tools.saturn_private_prologue_continue_fourth_c \
      --cue "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1).cue" \
      --track1 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 1).bin" \
      --track2 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 2).bin" \
      --executable "/private/yabause" \
      --expected-runner-sha256 "LOWERCASE_SHA256_FROM_EXACT_HEAD_CI" \
      --triple-c "/private/runs/triple-c" \
      --fourth-c "/private/runs/fourth-c" \
      --timeout 7200

The report exports only booleans, counts and frame numbers. Never commit or upload original BIN/CUE files, private screenshots, raw FAD logs, extracted game resources, local paths or frame hashes. Keep authenticity Issue #11 open until the first controllable tactical battle is independently verified.
