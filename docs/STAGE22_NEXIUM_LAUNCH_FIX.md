# Stage 22 — Fix shell quoting before NeXium startup

## Verified root cause

Stage 20 run #39394669004 built and downloaded the genuine Switch NRO, installed emulator dependencies and obtained the NeXium nightly. The emulator was **not launched**: the nested Bash command failed with `syntax error: unexpected end of file from 'if' command`. An inner single-quoted echo string prematurely closed the surrounding single-quoted bash -c block.

## Fix and evidence

- Extract the launch/capture sequence to `scripts/nexium_capture.sh`.
- Add independent `bash -n` syntax verification before the runner calls it under Xvfb, eliminating nested script-string quoting.
- Preserve runtime-evidence/nexium.log, the screenshot, an explicit failure-reason text on early exit, and capture status for later investigation.
- Existing Stage 21 screenshot classifier checks for two separated blue and red figures. It still requires independent review and a control input test.

## ROM-free tests

New `tests/test_nexium_launcher.py` performs a real `bash -n` syntax check and verifies the script includes the expected evidence paths. The two tests pass locally; these tests do not run NeXium or authenticate a game frame.

## Next

Review the new GitHub Actions `run-in-nexium` result and any evidence artifact. Do not claim visual or input runtime success until real screenshots/logs are available. Original Sega Saturn media remains private and the original first mission is not yet recreated.
