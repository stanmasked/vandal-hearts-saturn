# Stage133 — pinned public Yabause Stage124 emulator build and private handoff

The Stage124 original Saturn disc Track 1, Track 2 and CUE have now been
successfully restored from owner-only Google Drive to a restricted local
working directory. Track 1 was reconstructed from its two split ZIP parts
because direct Google Drive streaming of the 621,755,904-byte original
exceeds the connector's 256-MiB limit. The local Track 1, Track 2 and CUE
match the independent original private Stage124 manifest SHA-256 values and
byte counts. No original media was placed in GitHub or GitHub Actions.

The missing operational component is the pinned instrumented Yabause
executable. Stage133 builds it on a public GitHub runner using ONLY public
upstream Yabause sources pinned at
7e38821dbac265490f115e163c523a939acda759 and public lodepng sources
pinned at e584a8490db1b76b81bf298c11c09d3b55d9c270. It applies the
existing version-checked public split-CUE CD reader patch and the nested
Stage124 ninth-C controller/frame/diagnostic patch. It builds a C68K-enabled
headless runner with no original game or private Drive data in CI.

The build checks the synthetic Stage124 patch contracts, basic runner CLI,
and prints a public-binary SHA-256. Only the compiled *open-source* emulator
executable is exported, as a one-day GitHub Actions artifact. Never export
a source BIN/CUE, original frame PNG, private CD trace, private media
digest, Drive authentication token, or original-disc audit report as a
public artifact. The executable must be downloaded into an authorized
private work directory, fingerprinted again and exercised against the
privately restored CUE only on that private host.

An original Saturn boot or Stage124 recapture MUST NOT be claimed from
synthetic public CI. Real new Stage124 paired capture still requires
authoritative original-media checks, the private output audit, a new
archive, private Drive upload, independent readback, owner-only permission
verification, and a separately minted private Stage125 receipt.

If public artifact delivery is unavailable, do not copy original media
into GitHub as a workaround. Keep the restored private source intact and
declare original-game runtime blocked.
