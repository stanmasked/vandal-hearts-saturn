# Stage117 — advance the next prologue dialogue

## Stage116 private result

The Stage116 private pair completed 48,000 frames. At frame 31,320 the control still displayed Magnus's “Ah...a hidden room.” line, while the second-C run had advanced to “Hmm? What's that?”. The new line remained on screen at frames 36,000 and 48,000. This confirms the second C advances the dialogue, but it does not establish a controllable battle.

The private pair has 400 valid 352×240 PNG checkpoints and 402 ordered video/SH2 samples per run. The pinned English v1.1 media and runner hashes matched after the run. Three pre-intervention checkpoint differences (6240, 9720, 9960) are confined to the letterboxed opening FMV viewport; all other checkpoints before frame 31,200 match. The Stage116 audit now allows only those three reviewed intro-FMV checkpoints and rejects any other pre-input mismatch.

## Controlled Stage117 pair

Use the same Stage117 public runner and original media for two separate cold boots. Both runs receive START at frame 12,060, the first C at frame 12,240, and the second C at frame 31,200.

- **Double-C control:** the third-C schedule is configured at frame 39,000 but disabled.
- **Triple-C intervention:** the same third-C schedule is enabled and released at frame 39,006.

The runner refuses to enable the third C unless the second C is enabled. The new input uses the native Yabause peripheral API and active-low state checks. Both processes receive identical environment keys; only the third-C enable bit differs.

## Audit and visual-review gates

- Both runs must match at every stable checkpoint before frame 39,000. The only permitted earlier differences are the reviewed intro-FMV checkpoints 6240, 9720 and 9960.
- Both runs must complete 48,000 frames and produce 400 sequential PNGs plus 402 ordered video/SH2 samples, with exact file sets and verified controller receipts.
- The third C must cause a reproducible framebuffer divergence by frame 45,000; otherwise the audit fails closed.
- Review the private frames after frame 39,000 to determine whether “Hmm? What's that?” advances and whether a new dialogue or tactical control state appears. A frame difference alone is not proof of a playable battle.

## Private execution

Download the GCC or Clang executable from the successful exact-head Stage117 workflow and use the SHA-256 printed by that same job. Create two fresh sibling output directories with mode 0700 and equal-length absolute paths outside the checkout.

    python3 -m tools.saturn_private_third_dialogue \
      --cue "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1).cue" \
      --track1 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 1).bin" \
      --track2 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 2).bin" \
      --executable "/private/yabause" \
      --expected-runner-sha256 "LOWERCASE_SHA256_FROM_EXACT_HEAD_CI" \
      --double-c "/private/runs/double-c" \
      --triple-c "/private/runs/triple-c" \
      --timeout 7200

The report exports only booleans, counts and frame numbers. Never commit or upload original BIN/CUE files, private screenshots, raw FAD logs, extracted game resources, local paths or frame hashes. Keep authenticity Issue #11 open until the first controllable tactical battle is independently verified.
