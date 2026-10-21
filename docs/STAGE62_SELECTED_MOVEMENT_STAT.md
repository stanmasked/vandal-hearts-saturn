# Stage62 — selected ally movement allowance

Base: Stage61 `d59edc1`, currently awaiting independent GCC/Clang, Switch
and real NeXium gates. Stage62 is a separate branch and leaves Stage61 intact.

Adds `MOV 4` to the selected allied unit card at logical x540/y683,
between `HP` and `ATK`; all earlier HUD positions remain unchanged.
The value is the unit's authored movement allowance (Scout 4, Guard 3),
not the remaining movement after moving. The existing moved/not-moved marker
continues to communicate whether movement has been spent this round.

The projection reads the actual `Unit::move_points` field, carries no
pointer between frames, and does not modify movement costs, reachability,
turn state, fingerprints, or attack logic. Native tests cover Scout/Guard,
post-move display, invalid selections, Victory and immutable repeated reads.

The real NeXium auditor re-runs Stage55 and checks the complete 3x5 bitmap
for `MOV 4` in first selection, post-attack, round 2 and round 4 images;
the stat must be absent before selection and after Victory/Defeat. Synthetic
adversarial tests reject wrong numerals, missing labels, single-pixel edits,
and ghost stats.

No Stage62 ALL GREEN claim until its own GCC/Clang, Switch NRO and real
NeXium screenshot gate passes. This remains an original ROM-free prototype.
