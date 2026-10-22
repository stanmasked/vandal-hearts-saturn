# Stage116 — verify a follow-up C press during the opening dialogue

## Stage115 visual-review finding

The 48,000-frame Stage115 pair is structurally valid: each private run produced 400 sequential 352×240 PNG checkpoints, 402 ordered video samples, 402 SH2 samples and exact controller receipts. The original English v1.1 media hashes and Stage115 GCC executable hash matched their pinned values after the runs. The captures remain private.

Visual review found that the START+C path reaches the opening tactical map, but the screen still shows Magnus's dialogue (“Ah...a hidden room.”) at frame 48,000. This does not establish that the first battle is controllable. The next experiment must isolate whether an additional C press advances that dialogue.

## Controlled pair

Use the exact Stage116 GCC executable and the same original media for two independent cold boots:

1. **Control:** START at frame 12060, C at frame 12240, release at 12246, then no more input.
2. **Intervention:** same START and initial C, plus one additional C pulse at frame 30000, released at 30006.

Only the second run configures VH_SATURN_FOLLOWUP_C_AT_FRAME. The runner rejects a follow-up pulse without the initial C confirm, with an A confirm, when a second START is also configured, outside the frame window, or too close to the initial confirm. The pulse uses the native Yabause peripheral API and active-low bit checks.

## Audit gates

- Both runs must match at every checkpoint before frame 30000; this isolates the follow-up input.
- Both runs must complete 48,000 frames and produce the exact 408-file set, including 400 sequential PNGs and 402 ordered video/SH2 samples.
- The auditor requires a reproducible framebuffer divergence within 6,000 frames after the follow-up pulse. If the screen does not change in that window, the experiment fails closed.
- A numeric difference only proves an input-associated change. Review private frames to determine whether the dialogue advanced and whether the tactical turn/HUD and player controls became active. Do not claim the first battle is playable from a different frame alone.

## Private execution

Download the GCC executable from the successful exact-head Stage116 workflow and use the SHA-256 printed by that same job. Create two fresh, empty directories with mode 0700 outside the checkout.

    python3 -m tools.saturn_private_followup_c_window \
      --cue "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1).cue" \
      --track1 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 1).bin" \
      --track2 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 2).bin" \
      --executable "/private/yabause" \
      --expected-runner-sha256 "LOWERCASE_SHA256_FROM_EXACT_HEAD_CI" \
      --initial-c-only "/private/runs/initial-c-only" \
      --followup-c "/private/runs/followup-c" \
      --followup-c-frame 30000 \
      --timeout 7200

The report exports only booleans, counts and frame numbers. Never commit or upload original BIN/CUE files, private screenshots, raw FAD logs, extracted game resources, local paths or frame hashes. Keep authenticity Issue #11 open until the first controllable tactical battle is independently verified.
