# Stage64 — hovered movement-cost HUD

Base: Stage63 `7ff19a909fc4418101ab61b29e3c97dbfea69ccb`.

## Behaviour
- With a live selected ally and cursor on a legal destination, show `COST n LEFT m`.
- Values are from `Battle::preview_move`, the same read-only legality/cost source used by committed movement.
- No HUD on current tile, blocked/occupied/unreachable destination, no selection, spent movement, or terminal battle.
- The compact renderer deliberately suppresses values above 999 instead of truncating a number and displaying a false cost.
- No changes to battle fingerprints, original game assets, or Saturn-specific claims.

## Evidence
- C++ `move_preview_hud_contract`: Scout/Guard costs, terrain cost, invalid destinations, spent movement, terminal state, immutable fingerprints and numeric display bounds.
- Python adversarial pixel tests: exact cost and remaining budget, missing/wrong values, a one-sampled-pixel corruption, no-selection hide and post-move hide.
- Existing real NeXium action trace now records the selected Scout while the cursor is over the legal adjacent tile. The Stage64 auditor validates that frame's state hash, selection outline, cursor coordinate, every label glyph pixel, and hide/show states before/after the move.
- CI must pass on this exact head before marking Stage64 verified.

## Boundary
This remains a synthetic ROM-free training scene. Its terrain costs and move rules are not yet authenticated against the original Sega Saturn release.
