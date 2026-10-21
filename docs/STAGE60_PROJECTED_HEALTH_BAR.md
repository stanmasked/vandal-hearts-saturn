# Stage60 — projected HP bar, remaining / lost split

Base: Stage59 `4ab1de9`, **ALL GREEN** with 17/17 C++ and
406/406 Python tests on GCC and Clang; Switch NRO compiled; actual
NeXium guest screenshots confirmed HP14 and HP0 with prior Stage54-58
regressions.

Stage60 adds a 220x5 horizontal bar along the bottom of Stage56's enemy
card (logical x1020..1239 / y705..709), clear of existing glyphs,
UI samples and game model regions:

- Green: number of the target's *current* HP remaining after the next legal attack.
- Red: number of the target's *current* HP removed by that attack.
- No bar while not aiming a legal selected attack, after spent attack,
  on allied/empty tiles, or during Victory/Defeat.

Important: the current ROM-free Unit does **not** have maximum HP.
The bar therefore represents a split of *current health*, not a full
maximum-HP health meter. The displayed numerical HP predictions from
Stage59 remain authoritative.

The view reuses Stage59 `target_remaining_hud`, which is derived from
the same existing `Battle::preview_attack` that executes actual
damage. No duplicate damage formula, new controls, saved pointers,
original Saturn assets, game-rule or battle-fingerprint modifications.

C++ contract tests all 4 remaining HP and bar-width states:
154/125/55/0 green pixels respectively (220px full width), with all
terminal and invalid cases hidden. Adversarial image tests reject fake
colors and ghost bars. CI requires a real NeXium guest PNG check of
pre-hit 14/20 (green 154, red 66), lethal 0/2 (all red), hidden post-hit
and hidden Victory/Defeat, after re-running Stage59 and all prior
guest-state screenshot audits.

CI is pending on Stage60 head; do not mark green before real results.
