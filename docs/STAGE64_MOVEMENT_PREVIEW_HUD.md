# Stage64 — hovered movement cost cue (ROM-free)

## Purpose
Make the Stage63 movement legality contract visible without adding a new
control or changing battle state. When an allied unit is selected and the
cursor is on an empty legal destination, the lower-left card shows
`COST n LEFT m`: terrain-weighted route cost and movement points remaining
after the move.

## Behavior
- Data comes from `Battle::preview_move`; no duplicate pathfinding rules.
- Hide on the selected unit's tile, occupied ally/enemy, blocked or over-budget
  destination, absent/dead/enemy selection, spent movement and terminal phase.
- Hide rather than truncate values above 99.
- The view is read-only; cursor movement changes no tactical fingerprint.
- The panel occupies x16–205, y600–641, above the help strip and outside the
  battlefield and all existing HUD regions.

## Verification
- Native `movement_preview_hud_contract` covers weighted/ordinary routes,
  Scout/Guard budgets, immutable reads, invalid destinations, spent movement,
  terminal state and wide-value suppression.
- Stage44's NeXium duel captures a genuine frame one tile above Scout, returns
  to Scout, then continues its original attack flow.
- The pixel auditor checks exact `COST 1 LEFT 3` glyph bits, green cue marker,
  battle fingerprint, selected Scout and hidden cue on selection, return,
  occupied Raider tile and after attack. One-pixel corruption is rejected by
  adversarial tests.

## Scope
This proves the cue on a ROM-free training duel, not original Saturn gameplay.
It does not claim original 1997 pathfinding rules. Physical Switch hardware is
untested. Authentic first-battle evidence is tracked in
[Issue #11](https://github.com/stanmasked/vandal-hearts-saturn/issues/11).
