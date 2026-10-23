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
