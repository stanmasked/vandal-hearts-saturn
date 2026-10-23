# Stage125 — guarded tenth C after the “We're surrounded!” dialogue

## Starting evidence and limits

The Stage124 private paired original-disc run was documented as completed: 2 cold boots × 108,000 frames, 900 PNG checkpoints per boot, 799 identical checkpoints before the ninth-C intervention, and first divergence at frame 96,120. A private visual review observed the ninth-C intervention reach the “Other Merchant: We're surrounded!” dialogue. This is **dialogue progression only**, not proof of tactical battle entry or player control.

The Stage124 derived capture archive was locally verified in an earlier working environment, but **has not been verified in Google Drive**. The new execution environment does not contain it. The private Drive report and manifest survive. This missing archive is a hard gate against running or deleting new private capture data.

## Public Stage125 source scope

- Compose the pinned Stage124 source patch on the exact public Yabause revision.
- Require the prior ninth C to be **enabled in both paired boots**; optional tenth C differs only through `VH_SATURN_CONFIRM10_ENABLED=0/1`.
- Proposed tenth-C press frame: **108,000**, release: **108,006**; bounded completion at **120,000** frames.
- Reject empty or malformed frame/enable values, a tenth press less than 12 frames after the ninth press, a frame too close to the capture bound, duplicate patching, incorrect active-low C state, or failed diagnostic writes.
- Keep original SH2/video/CD instrumentation and all first-nine-C inputs unchanged.
- Compile the real public Yabause source with GCC and Clang. Run synthetic-only regressions, and keep the runner binary ephemeral (no public artifact).
- Never use original discs, BIOS, screenshots, FAD records, private traces, or capture hashes in the public CI.

## Future private paired experiment — **not authorized until Stage124 archive gate passes**

1. Recover or transfer the exact Stage124 private capture archive, then verify its file ID, expected size, SHA-256 and inventory by private Google Drive readback. Preserve unchanged original source records.
   The private runner now additionally requires `--stage124-drive-receipt` pointing to an owner-only local JSON receipt generated after authentic Drive readback. It must identify `stage: 124`, `owner_only: true`, `readback_verified: true`, a nonempty `drive_file_id`, positive `archive_size_bytes`, and matching 64-hex-digit `archive_sha256` and `drive_readback_sha256`. Store this receipt privately, outside the Git checkout. The private CLI also requires `--stage124-drive-readback-archive`, an absolute non-symlinked local file downloaded back from Drive, kept outside the public Git checkout. Before launching the emulator it hashes the full downloaded archive and checks its actual byte count against the receipt. It verifies the archive remains unchanged after the run. Merely possessing a text receipt is not sufficient. An authenticated owner-only Drive download and independent comparison against the Stage124 private manifest are still required.
2. Build and fingerprint the exact Stage125 runner from successful public source gate; record its SHA-256 privately.
3. Perform 2 independent cold boots of the pinned original disc, each to 120,000 frames. All nine earlier C presses must be identical; only tenth enable flag differs.
4. Require exactly **1,000** 120-frame checkpoint PNGs and **1,002** ordered SH2/video samples per process. Compare all **899** checkpoints strictly before the tenth-C input, require identical pre-START frames, verify active-low press/release receipts, bounded geometry, canonical diagnostics, unchanged source and executable fingerprints, and a framebuffer difference by frame **109,200**.
5. Review real private frames for actual text and scene transitions. A different framebuffer alone does not prove gameplay. Tactical-battle claims require a visible tactical turn/HUD and independent selection or movement response.
6. Upload all raw private captures, logs and derived checksums to the owner-only Drive folders before local deletion. Store reports and manifests separately; validate Drive readback.

## Current state

Only Stage125 **public source instrumentation, synthetic tests, and ROM-free CI** are being prepared. No Stage125 original-disc run has been performed and no battle/player-control result is claimed. Stage124 PR #80 remains Draft; this stage is stacked on its branch. Authenticity Issue #11 remains open.
