# Stage 23 — Mocked NeXium launcher integration tests

The Stage 22 launcher had only Bash syntax tests. This stage executes the **actual launch script** as a process with mock NeXium, xdotool and ImageMagick commands. No game media, emulator download, or copyrighted content is required.

Six synthetic integration tests cover: Bash syntax, successful screenshot and receipt, emulator exiting before a window appears, missing window despite a live emulator, screenshot tool failure, and rejection of malformed runtime timing parameters. All six passed locally.

The script now emits explicit `VH_EMU_FAILURE` causes, and the failure reason is written to `runtime-evidence/failure-reason.txt` for the existing GitHub Actions even-on-failure upload. Successful capture writes a receipt. It also supports bounded integer timing overrides, defaulting to 45 polling attempts, one-second polls and 12 seconds settling. CI production values are unchanged.

An already successful diagnostic NRO artifact from Stage 19 was downloaded and checked privately: 6,754,360 bytes; `NRO0`; SHA-256 `5fd70b87cb00865d6b25bafbd9f433117157b02cc8008779966eeaff0ad3bbe4`, exactly matching the CI verifier.

The Stage 22 live NeXium workflow was still queued at last check. Local NeXium binary download was unavailable in this environment. **These mocks are not proof of emulation or visual/interactive gameplay.** Next: inspect actual NeXium job logs, screenshot and input response. First authentic Sega Saturn battle remains unimplemented and its assets private.
