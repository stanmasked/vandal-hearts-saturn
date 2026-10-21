# Stage54 — damage preview HUD and independent real guest proof (ROM-free)

## Background

[Stage53 native forecast and both guest outcomes ALL GREEN](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39559533129) on `ca05d583`. Existing Stage50 four-round Victory and Stage52 eight-round Defeat are protected by separate real NeXium screenshot gates, including immutable FNV-64 state fingerprints and rejected terminal commands. Stage54 adds a **UI visualization only**, not original Sega Saturn content.

## Design / inputs

The native C++17-only `include/vh/attack_preview_hud.hpp` exposes pure `attack_preview_hud(const Battle&, int selected, Pos cursor)`. Only a live player-selected unit, legal attack at the hovered enemy tile, and current `Phase::Player` can produce visible HUD instructions. Unselected cursor, empty tile, an already-used attacker, terminal Victory/Defeat or out-of-range aim must never show it.

The SDL renderer draws the preview in the existing bottom information ribbon (logical position x145 y680, 176×14 pixels):
- **Green** RGB(117,221,109): portion of target HP that will survive the hit.
- **Purple** RGB(179,103,244): portion of current HP to be removed.
- **Gold outline** RGB(251,220,90): the hit defeats the entire opposing side (not merely one of multiple enemy units).
- Empty/default HUD: original help-ribbon RGB(45,64,83).

Bar sizes are relative to **the target's current HP**, since the ROM-free prototype does not have a maximum-HP stat. `remaining_width = floor(predicted_remaining_hp×176/current_hp)`, `damage_width=176-remaining_width`, with a 64-bit intermediate. Preview never changes the native `Battle`, selection, round, unit HP or its on-screen fingerprint. `Battle::attack` uses the Stage53 shared forecast, so real damage and display calculations agree.

## New coverage

`tests/attack_preview_hud_tests.cpp` is new native CTest `attack_preview_hud_contract` on GCC and Clang: verified four-round original duel all the way to final lethal 2HP, hidden after each committed hit, 50 repeated forecasts with an unchanged full state hash, 2v2 condition for *not* ending battle after killing only one enemy, hidden on Defeat and Victory.

`tests/test_nexium_attack_preview_hud.py` adds 11 synthetic/adversarial image tests covering nonlethal aim, lethal aim, missing forecast, forged segment colors, missing gold outline, HUD improperly remaining after an attack, missing screenshot sequence and a fully reconstructed two-round folder.

**Most importantly, Stage54 is gated by a NEW independent NeXium image-only verifier**, `tools/nexium_attack_preview_hud.py`. It reopens actual ROM-free guest X11 screenshots already captured by existing Stage44/50 scripts:
- `action-duel-selected[/-retry].png` must show NO forecast, with selected Scout outline and exact initial battle fingerprint;
- the LAST real `action-duel-aim-N.png` must show green at (160,686), purple at (280,686), dark normal outline at (150,676), selected Scout, enemy cursor and correct initial duel hash;
- `action-duel-attacked.png` must show NO forecast after consuming the action and have the correct post-hit hash;
- the LAST `action-victory-round4-aim-nav-N.png` must show a **purple full-width lethal preview** and a **gold outline**, exact fourth-round hash and Raider aim;
- `action-victory-round4-attacked.png` must show NO forecast again after real Victory, with the canonical terminal hash.

Each pixel uses the existing magenta X11 anchor registration (not raw uncalibrated coordinates). User-visible game state remains the **original ROM-free tactics demo**, not the Sega Saturn game. No real hardware Joy-Con proof is claimed.

## Completion criterion

The new head is **pending** GCC+Clang host CI, devkitA64 NRO builds and real NeXium image audit, in addition to all previously verified Victory/Defeat captures. A green Stage53 run does **not** mean Stage54 is green.
