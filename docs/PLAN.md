# Saturn-based Nintendo Switch native remake — plan

Base game: Vandal Hearts ~Ushinawareta Kodai Bunmei~, Japanese Saturn `T-9526G` (1997).
This is an independent project, not the PS1/PlayStation remaster.

## Verified status on 2026-10-21
- Stages 01–62 implement a ROM-free synthetic tactical vertical prototype;
  Stage62 passed GCC/Clang, NRO and genuine NeXium guest evidence.
- Stage63 extends shared, read-only move-cost validation (pending its own CI).
- **Do not equate** the synthetic training scene with the first Saturn mission.
- Original Saturn map geometry, battle parameters, story, graphics and audio
  remain unverified. Never publish the original disc or extracted assets.

## Stage 01 — ROM-free prototype (completed technical foundation)
- C++17 tactics core: grid elevations, terrain, path costs, units, sides, turn phases.
- Deterministic test-only damage model, placeholder enemy AI, training arena.
- Host CLI, optional SDL2 renderer and prospective libnx/SDL2 NRO Makefile.
- Automated host tests (no game media in CI).

## Stage 02 — Saturn content research (blocked on user's lawful disc dump)
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
