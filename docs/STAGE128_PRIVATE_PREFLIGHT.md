# Stage128 - strict previous-capture admission before original-disc Stage125

## Why Stage128 is required

The Stage125 runner already requires an owner-only private Drive receipt and the actual downloaded Stage124 archive, checking size and SHA-256 before launching the emulator. However, matching a supplied checksum is not proof the downloaded archive contains all of the required capture checkpoints and diagnostics. Its earlier synthetic receipt tests intentionally accepted a small invented byte string.

Stage128 adds a mandatory structural integrity preflight inside the real Stage125 execution path, immediately after the existing receipt and full-file digest check, before source-media checks, output creation or starting Yabause. The Stage126 independent TAR.GZIP auditor rejects any archive missing the complete 1,800-checkpoint Stage124 shape, 16 diagnostic files, sound PNG CRCs or safe bounded TAR structure. An archive changing during verification fails closed.

Five new invented-only tests cover complete archive admission, missing checkpoints, malformed PNGs even if the outer digest matches, bad fingerprints, and proof that a failed preflight stops before the emulator is inspected. Isolated CI also re-runs existing Stage125 synthetic receipt tests. No original media, images, private hashes or file paths are used in GitHub Actions.

## Independent evidence still required

This change DOES NOT recover the historical Stage124 archive. The owner-only Drive capture folder is still empty at latest verification; old capture bytes are absent from the current workspace. Stage127 Host GCC/Clang, Switch/NeXium, and mocked Drive roundtrip public CI passed on revision 79bf59055595c99bfc531660a552add2d343fd5a.

A receipt and structurally valid archive alone cannot authenticate Google Drive ownership, file ID, folder permissions, or provenance. Live authorized Drive metadata and a distinct download compared against the pinned correct private experiment manifest remain mandatory. Stage125 paired original-media experiment stays blocked until preservation is verified.

No real BIN/CUE, captured PNG, private hashes, secrets or receipts are permitted in the GitHub repository. A future Stage124 recapture is a NEW experiment with its own attestation; never represent its bytes as the lost historical capture.
