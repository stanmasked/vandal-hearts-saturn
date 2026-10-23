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

## Public CI result

At exact PR head `338b6aed18253d04698af9ddb690a5cbfefd3c2c`, both Stage118 runner jobs passed:

- [Clang runner job](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39899572882) — executable SHA-256: `b4a682579d1da7804d4fe0e7ff8864a50aa30dd715e15d7a7265febd89f1bdf5`; artifact ID `12478680452`.
- [GCC runner job](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39899567541) — executable SHA-256: `ba061492d4773a0bf0893ee38f93498d080c8d8cfdef3a2c4be3cd9f81a09669`; artifact ID `12478431623`.

Both jobs passed the synthetic-only Stage118 and inherited regression suites, built the genuine public Yabause C68K software runner, and passed the disc-free CLI/fail-closed frame-window check. These results validate the public executable and test harness only; they do not represent a run of the original game.

## Private Stage118 result

The exact-head Clang artifact was extracted locally and its executable SHA-256 matched the CI log. The English v1.1 CUE and both tracks matched all pinned SHA-256 values before and after the run. Two private cold boots completed 48,000 frames each.

The local audit verified 400 sequential checkpoint PNGs per run, 402 ordered video samples and 402 ordered SH2 samples per run, closed CD-capture gates, exact controller receipts, byte-identical `pre.png`, all 349 checkpoints before frame 42,000 byte-identical, and identical canonical CD/FAD logs with 34,850 events per run. The first post-fourth-C framebuffer divergence was frame 42,120; the images matched through frame 42,000. Frame 48,000 differed.

Private visual review confirms the fourth C advances the dialogue: the triple-C control still shows “Oh...that sparkle... This must be it!” at frame 48,000, while the fourth-C run shows “Th...these rays... What's happening?” by frame 43,200 and retains it through frame 48,000. This is another confirmed prologue dialogue transition, not a controllable tactical battle; the scene remains in its scripted 3D animation and dialogue state.

## Private execution

The English v1.1 CUE and both tracks are present in the private Google Drive folder `VH-Saturn`. Before running, materialize those exact three files into the private execution environment and re-check the pinned media fingerprints. Do not substitute the separate Russian v1.6 BIN/CUE set. Use one of the following exact-head Stage118 runner hashes and create two fresh empty 0700 output directories outside the checkout with sibling paths of equal length.

    python3 -m tools.saturn_private_prologue_continue_fourth_c \
      --cue "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1).cue" \
      --track1 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 1).bin" \
      --track2 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 2).bin" \
      --executable "/private/yabause" \
      --expected-runner-sha256 "b4a682579d1da7804d4fe0e7ff8864a50aa30dd715e15d7a7265febd89f1bdf5" \
      --triple-c "/private/runs/triple-c" \
      --fourth-c "/private/runs/fourth-c" \
      --timeout 7200

The report exports only booleans, counts and frame numbers. Never commit or upload original BIN/CUE files, private screenshots, raw FAD logs, extracted game resources, local paths or frame hashes. Keep authenticity Issue #11 open until the first controllable tactical battle is independently verified.

## Private Stage118 result (23 October 2026)

The exact-head Stage118 Clang executable matched SHA-256 `b4a682579d1da7804d4fe0e7ff8864a50aa30dd715e15d7a7265febd89f1bdf5`. The user-provided split Track 1 was recombined and unpacked into a private workspace; Track 1, Track 2, and CUE each matched the pinned source size and SHA-256. Two private cold boots each exited successfully after 48,000 frames.

An independent local audit verified the complete 400-PNG checkpoint sets, 402 ordered samples in each video/SH2 diagnostic log, native controller event and active-low state receipts, and byte-identical initial framebuffer and all 349 checkpoints before frame 42,000. The first divergence appeared at frame 42,120. Both runs recorded exactly 34,850 canonical numeric CD/FAD events, with matching CD logs; source media and executable hashes matched after the experiment.

Private visual review shows the fourth-C branch advances the in-room dialogue: after the prior “Oh...that sparkle... This must be it!” line, by frame 42,480 the intervention displays “Th...these rays... What's happening?” with a new ray/ring animation. The control remains on the earlier line. At frame 48,000 the new line is still visible. **No controllable tactical battle has been established.**

The private source workspace and captures were not published. The independent cross-check was executed locally; this result should not be described as a run of the exact repository Stage118 auditor unless that module is executed and passes separately. In a shared/setgid filesystem, output folders created with requested mode 0700 may inherit group setgid (2700); explicitly clear that bit with `chmod g-s` and ensure mode 0700 before calling the strict repository auditor.
