# Stage120 — Stage114–119 chain audit and merge gate

**Audit snapshot:** 2026-10-23 04:32 UTC  
**Scope:** public repository history, PR dependency chain, exact-head GitHub Actions state, and private-evidence boundaries.  
**This is an audit snapshot, not a claim that pending CI or private execution has completed.**

## Dependency chain

| Stage | PR / head | CI at snapshot | Gate |
|---|---|---|---|
| Stage114 | [PR #63](https://github.com/stanmasked/vandal-hearts-saturn/pull/63), `e6f056554fbb1c4a70d07c65dc92dca460cf95ab` | Runner, host tests and Switch NRO all passed | Public CI green |
| Stage115 | [PR #64](https://github.com/stanmasked/vandal-hearts-saturn/pull/64), `e18d10600c0a91665726cce55209d347baafd4d0` | Runner, host tests and Switch NRO all passed | Public CI green |
| Stage116 | [PR #65](https://github.com/stanmasked/vandal-hearts-saturn/pull/65), `97f5e79499f96bf2722675c4394b6247f4e092af` | Runner, host tests and Switch NRO all passed | Public CI green |
| Stage117 | [PR #68](https://github.com/stanmasked/vandal-hearts-saturn/pull/68), `a463b06224d71bd9ce9884b4cadc81cae5b0de03` | Runner, host tests and Switch NRO all passed | Public CI green |
| Stage118 | [PR #71](https://github.com/stanmasked/vandal-hearts-saturn/pull/71), `338b6aed18253d04698af9ddb690a5cbfefd3c2c` | Stage118 runner passed; NRO build passed but NeXium guest smoke was in progress; host GCC/Clang tests were queued | **Not yet all green** |
| Stage119 candidate A | [PR #72](https://github.com/stanmasked/vandal-hearts-saturn/pull/72), `2375ff5806a0e8091804078037507bf141e9502a` | Fifth-C workflow passed; host tests pending and Switch NRO queued | **Not yet all green** |
| Stage119 candidate B | [PR #73](https://github.com/stanmasked/vandal-hearts-saturn/pull/73), `a06d468e5e0eeec2faa478b40051abb3928d98b2` | Fifth-C workflow passed; host tests and Switch NRO queued | **Not yet all green** |

Exact run references:
- Stage114: [runner](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39852827605), [Switch](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39852827566), [host](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39852827705).
- Stage115: [runner](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39855025077), [Switch](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39855025146), [host](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39855025184).
- Stage116: [runner](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39864262593), [host](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39864262356), [Switch](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39864262263).
- Stage117: [runner](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39874243312), [Switch](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39874243356), [host](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39874243193).
- Stage118: [runner](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39899572882), [Switch/NeXium](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39899573033), [host](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39899572900).
- Stage119 A: [runner](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39900429677), [Switch](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39900429560), [host](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39900429543).
- Stage119 B: [runner](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39900068094), [Switch](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39900068235), [host](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39900068008).

## Stage119 candidate review

The two Stage119 PRs implement different experiments and must not both be merged:

- **PR #72 is the preferred candidate for the next private experiment.** It schedules the fifth C at frame 48,000—after the Stage118 observation that the ray dialogue remains visible through that frame—and captures through frame 60,000. Its auditor expects 500 checkpoints per cold boot, 502 ordered video/SH2 samples, all 399 pre-input checkpoints identical, and a post-input divergence by frame 49,200.
- PR #72's patcher and regression test explicitly reject an empty `VH_SATURN_CONFIRM5_ENABLED` value before indexing the string.

The current exact-head PR #72 runner workflow is [run #39900429677](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39900429677) at head `2375ff5806a0e8091804078037507bf141e9502a`. Its executable SHA-256 values, taken from the build-job logs (not the ZIP digests), are:

- GCC artifact [12479001461](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39900429677/artifacts/12479001461): `d235e520f2d705830fb05ccfef00b54cd4ce8f5cc9e8865630488195945de62c`.
- Clang artifact [12478697575](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39900429677/artifacts/12478697575): `bcf52bd23873a7b510340e0906f2c4e4943cf0d616d675f9b31958400558d27c`.

Independently hash the downloaded executable and compare it to the corresponding value before a private run; do not use the artifact ZIP digest as the executable digest.
- PR #73 instead schedules the fifth C at frame 45,600 and ends at frame 48,000. Static review found that its patcher checks whether `VH_SATURN_CONFIRM5_ENABLED` is null but does not check for an empty string before reading index 1; its source test also omits that guard. This is a fail-closed validation gap to fix if PR #73 is retained.

This preference is based on the observed Stage118 boundary and code review; it is **not** a claim that either private Stage119 pair has completed.

## Private-evidence boundary

The checked-in Stage119 candidate documents do not yet contain a verified private fifth-C pair result. Treat the fifth-C gameplay effect as **unverified** until a privacy-preserving report from the exact-head private auditor and a separate visual review are recorded.

The private run must:
1. Use the exact-head public runner and verify its executable SHA-256 against the selected CI job.
2. Verify original media fingerprints before and after the run without modifying the media.
3. Compare the paired cold boots at every pre-fifth-C checkpoint and validate the exact active-low controller receipts.
4. Inspect the post-input frames through frame 60,000 for dialogue progression and any tactical HUD/turn state.
5. Export only counts, booleans and frame numbers. Never commit or upload original BIN/CUE files, screenshots, extracted resources, raw FAD logs, local paths or frame hashes.

A dialogue change or framebuffer difference does not establish player control. Keep the first controllable tactical battle claim false until an active tactical HUD/turn state and a repeatable response to a separate movement/selection input are independently observed. Keep authenticity Issue #11 open.

## Merge gate and order

1. Wait for Stage118 host tests and NeXium guest smoke to finish successfully.
2. Wait for Stage119 PR #72 host GCC/Clang tests and Switch/NeXium checks to pass at its exact head.
3. Record the private Stage119 pair result and visual review without publishing private artifacts.
4. Resolve PR #73 as a duplicate or repair its input-validation gap; do not merge both Stage119 alternatives.
5. Keep the stacked dependency order explicit: Stage114 → Stage115 → Stage116 → Stage117 → Stage118 → the selected Stage119. Before each merge, confirm the exact head and all required checks again, then retarget/rebase the next stacked PR as needed.

No PR in this chain should be marked ready or merged solely because its custom runner workflow passed while host/Switch checks remain pending.

## Follow-up CI poll

After the timestamped snapshot above, Stage118's Switch NRO build and NeXium guest framebuffer smoke both completed successfully on head `338b6aed18253d04698af9ddb690a5cbfefd3c2c`. Stage118 host GCC/Clang jobs were still queued at the follow-up poll. Stage119 PR #72's exact-head runner workflow remains green and its current artifacts/hashes are recorded above, while host tests and the Switch NRO workflow remain queued. PR #73's runner workflow is green, but its host and Switch jobs are also queued. These queue states are not failures, but they prevent claiming full CI success.

## Stage120 follow-up — exact-head public CI complete (2026-10-23)

After the snapshot above, every planned public workflow completed successfully:

- Stage118 PR #71 at `338b6aed18253d04698af9ddb690a5cbfefd3c2c`: [pinned runner](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39899572882), [host GCC/Clang](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39899572900), [Switch NRO and NeXium guest smoke](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39899573033) all passed.
- Stage119 PR #72 at `2375ff5806a0e8091804078037507bf141e9502a`: [pinned runner](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39900429677), [host GCC/Clang](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39900429543), and [Switch NRO/NeXium](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39900429560) all passed.
- Stage119 alternate PR #73 at `a06d468e5e0eeec2faa478b40051abb3928d98b2`: its public runner, host and Switch workflows also passed, but its documented empty-value guard weakness remains; **PR #73 was closed without merging as superseded by PR #72**, preserving the alternative branch as a reference.
- Stage120 [host](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39901293983) and [Switch](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39901293997) passed on audit head `dd0fab0a549ed1083bd9287923c171b9648368d4` before this follow-up documentation edit. Since the audit PR head has changed, do not apply that prior CI pass to a newer exact head without readback.

Public CI success **does not substitute for a private original-disc Stage119 pair**, a scene-level review or a demonstrated response to an independent player movement/selection input. The first-battle claim remains false.

## Private Stage119 pair verified (23 October 2026)

The selected Stage119 source, [PR #72](https://github.com/stanmasked/vandal-hearts-saturn/pull/72) at `2375ff5806a0e8091804078037507bf141e9502a`, was used for a private original-disc comparison. The exact-head Clang Yabause executable from artifact 12478697575 matched its build-job executable SHA-256. Both original track files and the CUE matched their independently pinned sizes and SHA-256 before and after the experiment. No original media, screenshot, raw FAD event, local path or frame hash is included here.

Two separate cold boots used identical environments and the same START/four-C schedule, with the fifth-C enable flag disabled in the control and enabled in the intervention. Both processes ran to 60,000 frames. The actual in-repository `audit_private_prologue_continue_fifth_c` function was executed on their private outputs and **passed**, in addition to a separate independent local structural check:

- **500/500 PNG checkpoints** and **502 ordered SH2/video samples per log** validated for each boot.
- Initial images and **399/399** checkpoints strictly before the fifth-C press at frame 48,000 were byte-identical.
- Native fifth-C press/release receipts at frames 48,000/48,006 were validated, including active-low bit state.
- First post-input framebuffer difference: **frame 48,120**; final frame 60,000 remained different.
- Canonical private numeric CD/FAD event counts: **34,850** for four-C control and **40,840** for fifth-C intervention. The logs differed after the intervention, as expected.
- Media and executable fingerprints remained unchanged. The private CD capture gates closed and both runner processes exited normally.

Private visual review at frame 49,200: the four-C control still shows the ray dialogue ("Th...these rays... What's happening?"), while the fifth-C intervention has transitioned to a full-screen pillar-of-light scene. By frame 54,000, and still at frame 60,000, the intervention shows the next dialogue text ("...Ash... ...Ash!!!") on black. These observations confirm **fifth-C-driven prologue progression**.

**Evidence boundary:** This experiment does not verify an actively controllable first tactical battle. No tactical turn/HUD plus separate player movement/selection input response has been independently verified. Keep `first_battle_or_player_control_verified` false and authenticity Issue #11 open. The independent cross-check and the in-repo integrity auditor were run, but the entire in-repo `run_private_prologue_continue_fifth_c` wrapper was not re-executed; the two cold boots were performed with an independently reconstructed matching private environment schedule.

## Stage121 proposed next original-game gate

Once the same private source pipeline is preserved, test a **sixth guarded C confirmation after frame 60,000**, since the "...Ash... ...Ash!!!" dialogue remains visible through that checkpoint. Compare two new cold boots with five earlier C pulses identical; change only the sixth enable flag. Extend the bounded capture window sufficiently to observe the next story state. Apply the same strict prior-checkpoint equality, active-low controller receipts, source hashes and privacy limits. Do not assume the sixth C leads to a playable battle without its own visual/input-response evidence.
