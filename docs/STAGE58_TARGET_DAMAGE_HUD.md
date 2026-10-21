# Stage58 — numerical damage forecast and lethal KO indicator

## Base
Stage57 `980efb6` confirmed: GCC/Clang 15/15 native tests and
382/382 Python tests, compiled Nintendo Switch NRO and actual NeXium guest
frame audit of enemy attack availability. No Saturn ROM or game assets.

## Read-only behaviour
When an allied fighter can legally strike the hovered enemy, display the
number of hit points the **next actual strike would remove**, rather than an
uncapped raw attack-power value. The renderer writes `DMG 6` in the unused
top centre of Stage56's enemy panel. Before the decisive final strike it
shows `DMG 2` with a gold `KO`. It is hidden on idle inspection, spent
attack, illegal target, allied/empty tile or terminal Victory/Defeat.

The model `target_damage_hud` reuses Stage57 `enemy_attack_cue`, which
uses `Battle::preview_attack` (already the same engine rule as real attack).
It stores no pointers, changes no combat state, and adds no input mapping.

## Verification
- C++ native CTest `target_damage_hud_contract` proves predictions
  6/6/6/2 and 14/8/2/0 after successive strikes, plus the lethal flag,
  bad selections, out-of-range, terminal Defeat and immutable state hashes.
- Python adversarial bitmap tests reject forged 6↔2 numerals, ghosts on
  spent actions, missing/wrong KO, and missing labels.
- The real guest `tools.nexium_target_damage_hud` first reruns Stage57's
  screenshot-backed validation and checks exact digits + KO on actual
  preattack, postattack, lethal and terminal PNGs.

All gates pending fresh CI and NeXium execution on the Stage58 head.
The project remains a separate original ROM-free tactical prototype,
not an original Saturn game asset or engine port.
