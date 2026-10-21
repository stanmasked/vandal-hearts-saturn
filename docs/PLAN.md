# Saturn-based Nintendo Switch native remake — plan

Base game: Vandal Hearts ~Ushinawareta Kodai Bunmei~, Japanese Saturn `T-9526G` (1997).
This is an independent project, not the PS1/PlayStation remaster.

## Verified status on 2026-10-21
- Stages 01–64 implement a ROM-free synthetic tactical vertical prototype;
  Stage64 passed GCC/Clang (22/22 CTest and 459/459 Python per compiler),
  both Switch NRO builds and real NeXium guest pixel checks.
- Stage65 adds a metadata-only crosswalk for candidate Saturn resources; CI pending.
- Stage66 adds a provenance-linked observation-manifest validator with synthetic-only tests; CI pending.
- Stage67 adds evidence-coverage checks; Stage68 adds a neutral terrain bridge for locally verified numeric geometry, without guessing attack/AI rules. Both require their own CI.
- Stage69 verifies the Python-to-native terrain protocol with independent aggregates and negative mutation tests, using synthetic-only geometry; CI pending.
- Stage70 passed native movement/terrain equivalence (GCC/Clang 24/24 CTest, 503/503 Python; NRO/NeXium green).
- Stage71 verified signed elevations and synthetic 128×128 matrix on GCC/Clang (24/24 CTest, 509/509 Python per compiler), NRO and NeXium.
- Stage72 passed ordered terrain identity across seven fabricated sizes and four equal-sum permutations (GCC/Clang 25/25 CTest, 514/514 Python; Switch NRO and NeXium green).
- Stage73 crosswalks privately captured logical-sector reads with candidate ISO9660 extents and menu controls; FAD normalization requires an explicit label and Track-1 bounds. CI pending.
- Stage74 passed numeric multi-run sector read repeatability (GCC/Clang 25/25 CTest and 548/548 Python, Switch NRO and NeXium green); independent capture authenticity remains unproven.
- Stage75 passed private metadata preflight: GCC/Clang 25/25 CTest, 564/564 Python per compiler, Switch NRO and NeXium green. No source authenticity claim.
- Stage76 passed GCC/Clang 25/25 CTest and 575/575 Python per compiler, NRO and real NeXium, for a synthetic Yabause-shaped CD read logger/adapter; the third-party emulator and original game were not run.
- Stage77 verified manually gated read windows: GCC/Clang 25/25 CTest and 587/587 Python, NRO/NeXium green, with only fabricated C read callbacks.
- Stage78 is ALL GREEN on its exact head: 25/25 CTest and 593/593 Python under both GCC and Clang; fixed public upstream Yabause ISO callback compiled/executed; NRO and NeXium passed. Full Yabause and original Saturn game remain untested.
- Stage79 is ALL GREEN on its exact head: GCC/Clang host regressions, Switch NRO, and real NeXium guest checks passed. Correct primary-payload read gating in the pinned Yabause ISO callback does not authenticate a game scene.
- Stage80 is ALL GREEN: exact-head GCC/Clang host regressions, real pinned Yabause core static library compilation on both toolchains, Switch NRO and NeXium guest checks passed. A library is not an emulator executable.
- Stage81 verified real pinned Yabause runner executable linkage and host CLI execution with GCC and Clang; remaining whole-project regressions are checked separately. CLI smoke does not initialize emulated Saturn hardware.
- Stage82 successfully executed YabauseInit/YabauseDeInit in the real pinned runner with GCC and Clang on a dummy CD and no BIOS or game. NRO succeeded; full exact-head CI finishes independently. This is initialization only, not execution of a Saturn game.
- Stage83 GCC/Clang real Yabause CI verified one YabauseEmulate frame with fabricated SH-2 instructions and changed R0/PC; Switch NRO and NeXium passed, remaining host checks run independently. This is no authentic game boot.
- Stage84 ALL GREEN: GCC/Clang true ISOCD backend reads from a generated two-sector file with exact gated numeric-only FAD 150/151 receipts; host regressions, Switch NRO and NeXium also passed. This does not authenticate original Saturn gameplay.
- Stage85 ALL GREEN at exact head: two independent real Yabause ISO subprocesses per GCC/Clang agreed on 4096-byte synthetic sector SHA-256 and exact numeric FAD receipts; host GCC/Clang, Switch NRO, NeXium all passed. No authentic game data used.
- Stage86 private-source hash checks and gate/output containment were verified by the new 12 synthetic tests each on Python 3.11 and 3.13; host GCC/Clang passed and NRO built. NeXium final result must be checked separately. No original game boot proven.
- Stage87 adds an opt-in, locally pinned *executable* SHA-256 check before/after capture and requires the exact declared absolute CUE path as a complete CLI argument. It does not prove the binary's independently trusted build origin or that the emulator opened the CUE. Synthetic CI pending.
- **Do not equate** the synthetic training scene with the first Saturn mission.
- Original Saturn map geometry, battle parameters, story, graphics and audio
  remain unverified. Never publish the original disc or extracted assets.

## Stage 01 — ROM-free prototype (completed technical foundation)
- C++17 tactics core: grid elevations, terrain, path costs, units, sides, turn phases.
- Deterministic test-only damage model, placeholder enemy AI, training arena.
- Host CLI, optional SDL2 renderer and prospective libnx/SDL2 NRO Makefile.
- Automated host tests (no game media in CI).

## Stage 02 — Saturn content research (English v1.1 image already cataloged)
- The user supplied split Track 1, Track 2 audio BIN and CUE; prior private metadata audit is recorded in docs/STAGE02_DISC_FINDINGS.md.
- The image is translation-patched English v1.1, not proof of the unpatched Japanese master.
- Keep all BIN/CUE/CHD/ISO and extracted content private; do not ask the user to upload the same image again.
- Check catalog ID/track layout, hashes, filenames and data format; no upload to GitHub.
- Compare Saturn and PS1 battle/map/event/magic/item differences.
- Record authoritative scene-by-scene Saturn-specific features, including extra maps.
- Inspect compression, texture, sprite and music formats with read-only tools.
- Determine actual battle data layout before replacing placeholders.

## Stage 03 — Real first-battle vertical slice
- Import owned Saturn map and unit data offline into a neutral intermediate format.
- Port movement/attack/height/AI/status/turn order with golden replay tests.
- Add scene/camera/transitions and controller usability tests.

## Stage 04 — Full game systems
- Units/classes/levels, magic, inventory, shops, battles and dialogue/event triggers.
- Full campaign, all Saturn-only content and endings proven from game data.
- Independent save schema with versioning and migration.

## Stage 05 — Graphics, audio, localization
- Classic and Original Style HD modes with 4:3 and 16:9 composition options.
- Restore assets locally from legally held copy; no bundled media in source repo.
- Saturn-faithful sound/music playback from on-device local asset pack.
- JP/EN/RU content localization, font coverage and text layout.

## Stage 06 — Verification and release readiness
- Automated combat golden tests against real Saturn reference captures.
- Switch NRO CI via devkitPro and controlled NeXium runtime checks.
- Performance target 60 FPS (not yet proven), 720p handheld, 1080p docked.
- Physical Switch correctness, input, suspend/resume, save and audio checks.

## Content safety
Source, synthetic test maps and build scripts can be public. Keep Saturn disc
images, extracted art/audio, translated game script, and private captures outside
GitHub and CI artifacts. Personal use alone does not make game assets redistributable.
