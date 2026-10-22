# Stage115 — extend the private first-battle run to 48,000 frames

## Why the longer window is needed

Stage114's private START+C run reached the story opening and a tactical grid map with soldier dialogue by frame 24000. The paired first-START-only control instead reached the title's level-29 attract-demo battle. The new-game path is therefore distinct, but the frame-24000 map/dialogue alone does not prove that the first battle has become controllable.

Stage115 changes only the pinned runner's fail-closed maximum from 24,000 to 48,000 frames. The same C68K core, exact ISOCD split-CUE path, START pulse, A/C native input hooks, video/SH2 instrumentation and numeric-only CD receipt remain in place.

## Controlled pair

Use the same Stage115 GCC executable and the same Stage02-verified English v1.1 media for two separate cold boots:

1. **Control:** START at frame 12060, no confirm input.
2. **New-game path:** START at frame 12060, then C at frame 12240, released at frame 12246.

Each run is capped at 48,000 frames and must produce 400 sequential checkpoint PNGs plus 402 ordered video/SH2 diagnostic samples. The auditor pins original media and executable before and after both processes, verifies active-low pad receipts, checks every PNG and frame-stat record, and requires the two runs to match through frame 12120 and diverge before the idle attract transition.

## What still requires visual review

The numeric audit reports only frame counts and comparison booleans. Inspect the private frames after frame 24000 to establish whether the opening dialogue advances into the first mission, whether the tactical HUD and turn state become active, and whether player input changes the selected unit or reachable tiles. Do not mark the first controllable battle verified based only on a tactical map, a dialogue box, or a different framebuffer.

## Private execution

Download the GCC executable from the successful exact-head Stage115 Actions run and use the SHA-256 printed by that same job. Create two empty 0700 directories. Keep the original BIN/CUE files, outputs and all captures outside the Git checkout.

    python3 -m tools.saturn_private_first_battle_window \
      --cue "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1).cue" \
      --track1 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 1).bin" \
      --track2 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 2).bin" \
      --executable "/private/yabause" \
      --expected-runner-sha256 "LOWERCASE_SHA256_FROM_EXACT_HEAD_CI" \
      --first-only "/private/runs/first-start-only-48k" \
      --confirm-c "/private/runs/start-plus-c-48k" \
      --timeout 7200

The report exports only booleans, counts and frame numbers. Never commit or upload original BIN/CUE files, private screenshots, raw FAD logs, extracted game resources, local paths or frame hashes. Keep authenticity Issue #11 open until the first controllable tactical battle is independently reviewed.
