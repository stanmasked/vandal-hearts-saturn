# Stage49 — full ROM-free tactical duel and terminal victory

## Confirmed baseline

[Stage48 native Switch/NeXium #39496473179](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39496473179) finished **SUCCESS** on `c92073dcb66b35180fc7afe86b16ec336b7853e6`. GCC and Clang also passed [#39496473185](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39496473185). The emulator successfully played round 2: enemy retaliated against Scout (HP22→19), then Scout attacked Raider (HP14→8), and another same-round attack was rejected. All 3 independent Xvfb launches passed; documented PNG/receipt artifact [#12298944591](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39496473179/artifacts/12298944591).

## New independent Stage49 host regression

The separate [`tests/duel_victory_tests.cpp`](../tests/duel_victory_tests.cpp) tests the **real native C++ battle engine**, not synthetic Python battle state. It starts an original ROM-free two-unit fixture `stage44_attack_duel()` and drives shared `TrainingAction` selection, movement, attack and end-of-round code until victory:

| Player round | Scout HP after enemy's previous action | Raider HP after Scout attack | Following Raider action |
| ---: | ---: | ---: | --- |
| 1 | 22 | 14 | Scout 22→19 |
| 2 | 19 | 8 | Scout 19→16 |
| 3 | 16 | 2 | Scout 16→13 |
| 4 | 13 | 0 | **Victory**, no enemy turn |

The winning attack must clamp Raider HP to zero, set `Phase::Victory`, produce `Victory!` UI status, and remove the dead Raider from `unit_at()`.

The test then intentionally attempts repeated Attack, EndTurn, Confirm, enemy and player direct `Battle::attack`, direct Move and direct EndTurn. **All must reject** without mutating the complete canonical battle fingerprint. A final UI-only Cancel may clear the selection, never undoing Victory. This protects against duplicate kills, HP underflow, post-victory enemy damage and phantom extra rounds.

This is a deterministic **host CTest regression only**; it does **not** claim a guest screenshot-proof of rounds 3–4, and it does not alter the verified Stage48 NRO scene, input driver or NeXium checks. A later separate bounded guest route may be added if host and Switch CI pass.

## Scope

Original minimal homebrew tactics engine, intentionally ROM-free. No original Sega Saturn maps, sprites, game scripts or proprietary disc resources; keyboard-in-NeXium tests do not establish Nintendo Switch physical controller behavior.
