# Stage119 — controlled fifth C press after the ray dialogue

## Starting evidence

Stage118's private 48,000-frame experiment advanced the dialogue from “Oh...that sparkle... This must be it!” to “Th...these rays... What's happening?” by frame 42,480 after fourth C at frame 42,000. Both runs matched all 349 pre-fourth-C checkpoint PNGs. The local independent audit verified 400 PNGs, 402 ordered video/SH2 samples and exactly 34,850 matching CD/FAD events in each run. At frame 48,000 the new ray dialogue remained visible. **No controllable battle has been established.**

## Controlled experiment

Both separate 48,000-frame cold boots receive precisely the same prior schedule:

- START at 12,060, release 12,066.
- C at 12,240, release 12,246.
- C at 31,200, release 31,206.
- C at 36,000, release 36,006.
- C at 42,000, release 42,006.

A fifth C at frame 45,600, released at 45,606, is scheduled in **both** runs. The baseline sets `VH_SATURN_CONFIRM5_ENABLED=0`; the intervention sets it to `1`. All other input/environment fields match. Use equal-length sibling output paths `fourth-c` and `fifth-cc` so HOME/TMPDIR/capture path strings have the same shape.

## Acceptance criteria

- Verify exact input-media and public runner SHA-256 before and after execution; never run original media in public CI.
- Verify 48,000 emulated frames per cold boot, exactly 400 valid PNG checkpoints and 402 ordered SH2/video diagnostic samples per run.
- Require byte-identical pre-boot PNGs and **all 379 checkpoints before frame 45,600** to match.
- Require exact active-low press/release controller receipts and an observed post-input framebuffer difference by frame 46,800.
- Privately examine frames 45,720, 46,080, 46,800 and 48,000 for dialogue advancement, animations or a tactical HUD.
- Do **not** identify player control from dialogue or images alone. A first controllable battle requires active turn/HUD indicators **and** a separate repeatable response to a player movement or selection input.

## Private command

Use the executable SHA-256 from an exact-head successful Stage119 GCC or Clang Actions run.

    python3 -m tools.saturn_private_fifth_confirm \
      --cue "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1).cue" \
      --track1 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 1).bin" \
      --track2 "/private/VH/Vandal Hearts - Ushinawareta Kodai Bunmei (English v1.1) (Track 2).bin" \
      --executable "/private/yabause" \
      --runner-sha256 "EXACT_HEAD_RUNNER_SHA256" \
      --fourth-c "/private/runs/fourth-c" \
      --fifth-c "/private/runs/fifth-cc" \
      --timeout 7200

Create output directories fresh with mode 0700, clearing an inherited group-setgid bit where necessary. Retain all original BIN/CUE and frame evidence privately. The JSON report must contain only counts, booleans and frame numbers; no raw FAD data, game pixels, frame hashes, or local paths.

Issue #11 stays open until the first controllable tactical battle is independently verified.
