# Stage55 — selected-fighter information HUD (ROM-free)

## Goal / scope

Continue from the **fully guest-verified Stage54 baseline** `b3860dbf`: green on GCC/Clang (12/12 CTest and 335/335 Python tests per compiler) and Switch/NeXium, including original ROM-free four-round Victory, eight-round Defeat and registered screenshot proof of the Stage54 attack forecast. Preserve every prior fingerprint and do not import any Sega Saturn executable/assets.

Stage55 renders **actual current fighter information** when the player selects a living allied unit. It is a display-only feature; no changes to battle mechanics, unit layouts, golden replay hashes or controller mappings.

## Read-only native model

`include/vh/selected_unit_hud.hpp` exports `selected_unit_hud(const Battle&, int selected)`. The result includes visibility, unit name/ID, real HP, attack, defense, attack range, movement spent and attack spent. It returns an invisible/zero view on no selection, unknown ID, enemy ID, dead player or terminal Victory/Defeat. The model never modifies `Battle` and does not hold a stale pointer between frames.

`src/ui/sdl_main.cpp` adds an SDL-rendered, asset-free **3×5 bitmap uppercase/numeric font** in the existing lower ribbon:

- Name (e.g. `SCOUT`), `HP 22`, `ATK 8`, `DEF 3`, `RNG 1`.
- Selection blue stripe at x354..361, y673..706.
- Attack readiness at x953..966,y683..696: cyan RGB(76,222,230) when unused, purple RGB(179,103,244) after attacking.
- Movement availability at x976..987,y683..696: grey-blue RGB(74,94,111) when unused, gold RGB(251,220,90) after moving.
- Entire HUD background is dark RGB(23,30,41); without a selected living ally it remains the previous help-strip RGB(45,64,83).
- Panel x350..993,y668..711 is strictly **right of Stage54 attack forecast** x141..324 and far below the top-right fingerprint image. It does not replace HUD colors or interrupt selected/hovered aim.

The combat engine itself and existing replay state digest are unchanged.

## Mandatory native tests

`tests/selected_unit_hud_tests.cpp` provides a new CTest `selected_unit_hud_contract`, covering visible/hidden selection, exact Scout and Guard attributes, repeat-read immutability (100 iterations), movement/attack-used flags, round reset after Raider counterstrike and HP22→19, cancel action, stale ID and enemy IDs, and both terminal phases with the established Stage50 / Stage52 entire-state fingerprints. All existing native Stage53 forecast and Stage54 preview tests remain enabled.

## Mandatory true NeXium PNG verifier

`tools/nexium_selected_unit_hud.py` runs only **after Stage44/50 and Stage52 separate real guest probes**, reopening images from their published evidence directories. The script tests the registered full-state digest and selected Scout outline for:

1. Initial duel: HUD must be hidden.
2. Real `action-duel-selected[/-retry].png`: HUD visible, HP22 digits, white HP/ATK/DEF/RNG labels, attack-ready cyan and movement-ready grey-blue.
3. Real `action-duel-attacked.png`: HP22 remains, action-used **purple**, selection remains until end turn.
4. Real `action-round2-ended[/-retry].png`: HUD hidden after selection reset.
5. Real `action-round2-selected[/-retry].png`: HP19 correctly updated after the enemy counterattack, attack-ready cyan.
6. Real `action-victory-round4-selected[/-retry].png`: HP13 and selected unit, before victory strike.
7. Real `action-victory-round4-attacked.png`: HUD hidden despite a possibly stale selected ID, with canonical Victory hash `6097117b6c951fb6`.
8. Separate real `action-defeat-round-8.png`: HUD hidden with canonical Defeat hash `3b0411b006f113c1`.

Every raster coordinate uses calibrated magenta framebuffer anchors to handle the existing X11 scaling. `tests/test_nexium_selected_unit_hud.py` adds 15 adversarial/synthetic image cases, including a complete independent staged replay, forged HP digits, misreported attack-used colors, missing labels, wrong state digest and ghost HUDs after terminal phases. Synthetic tests are **not** treated as evidence of a real guest run.

## Gate status

Stage55 is **not complete until** host GCC+Clang and the Switch NRO + guest NeXium workflow pass on the SAME Stage55 head. Only at that point may the read-only selected-fighter panel be described as verified in the actual guest. This remains an original ROM-free tactical prototype, not the original Sega Saturn game or evidence of physical Switch controller compatibility.
