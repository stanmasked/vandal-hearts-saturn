# Stage56 — enemy-hover HUD, ROM-free

## Contract

Starting from Stage55 `abeb0973` (13 C++/352 Python tests on GCC and Clang, Switch NRO and real NeXium verified), display current **living enemy** characteristics simply by placing the tactical cursor over an enemy unit. An allied selection is optional. No combat, movement, controller or serialized state changes.

The new `enemy_hover_hud(Battle, Pos)` view is independent of `selected_unit_hud(Battle, selected)`. It exposes the hovered enemy's real name, ID, HP, ATK, DEF, RNG only when the phase is Player; it is invisible for empty/off-map/allied tiles and terminal Victory/Defeat. No cached pointers or stale HP.

SDL draws the new right-hand card x1002..1273, y668..711 (dark background, red identity marker and bitmap glyphs), after the Stage55 ally panel x350..993. Stage54 damage forecast at x141..324 and on-screen state digest remain untouched. The compact panel deliberately does not use Saturn assets or a font dependency. Enemy HP changes as a consequence of attacks only; reading or painting the HUD does not change any battle fingerprint.

## Verification

`enemy_hover_hud_contract` adds deterministic native cases for Raider and Archer, no-selection hover, cursor departure, identical battle digests across 100 repeated reads, exact HP after the Scout strike, and hidden HUD after the established four-round Victory and eight-round Defeat. Previous golden hashes are asserted unchanged.

`test_nexium_enemy_hover_hud.py` adds synthetic adversarial image tests for correct and forged enemy HP, mislabelled panels and terminal ghost overlays; synthetic fixtures are not proof of NeXium.

`tools/nexium_enemy_hover_hud.py` is attached **after** Stage55's real guest checks. It reopens REAL action PNGs from Stage44/50/52 and uses the calibrated on-screen fingerprint and cursor geometry. It requires enemy HP 20 (aim), 14 (first hit/end of round), 8 (second hit), 2 (lethal pre-aim), plus absence on Scout hover and terminal Victory/Defeat. The actual NeXium check remains pending until that new workflow is green; do not confuse native model or synthetic raster tests with a real Switch execution.

## Scope

Original, standalone ROM-free prototype inspired by tactical RPGs; neither a port of the original Sega Saturn game nor a confirmation on physical Nintendo Switch hardware.

## Stage56 first real guest run and calibrated fix

Run [#39595863405](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39595863405) passed the NRO build and all prior guest Stage44/54/52/55 audits. New Stage56 pixel audit accepted the actual `HP 20`, `ATK 6`, and `DEF 2` glyphs from the first live Raider aim, but failed on the rightmost `RNG 1` glyph. An independently reopened original 1279x700 PNG shows the correct visible text; exact registered-sample inspection gave all 15/15 RNG bitmap bits at x-offset **-1**, compared with only 11/15 at the old x-offset 0. The same 15/15 offset held across the saved HP20, HP14, HP8, and HP2 guest screenshots. This is an **auditor sampling bug**, not evidence that the renderer failed. The bounded horizontal scan `-1,0,+1` retains **100% glyph-bit equality** rather than relaxing matching thresholds; new synthetic adversarial tests exercise shifted correct and forged RNG digits.

The fix is pending a new host and NeXium workflow pass on the same new revision.
