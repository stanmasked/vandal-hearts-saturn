# Stage59 — projected enemy HP after a legal attack

Stage58 (`5957c46`) completed independent GCC/Clang 16/16 native,
394/394 Python, Nintendo Switch NRO and actual NeXium guest pixel checks.
Stage59 retains all of these unchanged.

A read-only white `HP 14` line occupies x1140..1178 at y675..684 in
the enemy stats card alongside Stage58 `DMG 6`. It changes to `HP 0`
before the final strike, with Stage58's existing gold KO label.
No original game art, ROM, rule changes or duplicate damage computations.

The new `target_remaining_hud` projection uses **only** Stage58
`target_damage_hud`, which uses Stage57's shared forecast backed by the
battle engine. Its tests check the entire 14/8/2/0 HP progression,
ranged/invalid selections, terminal states, and unchanged battle hashes.

Synthetic Python image tests require exact glyph-bit equality for correct
and adversarial HP digits. The real PNG audit first rechecks Stage58 and
all earlier NeXium proofs and then audits the first hit, lethal hit,
postattack and terminal frames.

Stage59 verification pending its own GCC/Clang + Switch + real NeXium CI.
