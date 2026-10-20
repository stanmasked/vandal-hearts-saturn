# Stage47 — second-round native duel contract (ROM-free)

Stage46 provides the stable base: [host CI #39488599272](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39488599272), [Switch/NeXium #39488599120](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39488599120), all green with 3/3 independent emulator launches and the genuine attack/reselect screenshot gates.

Stage47 extends the **host C++ regression** for the unchanged `stage44_attack_duel()` battle engine. Starting after the previously verified Scout hit (Raider 20→14 HP) and forbidden repeated attacks, it tests:

1. Press X / `EndTurn`: selected Scout is cleared.
2. The placeholder AI's adjacent Raider strikes Scout once for `6 - 3 = 3` damage (Scout HP 22→19).
3. The game returns to the player phase in round 2, with Scout's `acted` reset but Raider damage preserved (HP 14).
4. A Y attack without a selected ally still fails.
5. Re-select Scout, aim at Raider, attack once. Raider HP 14→8; Scout HP remains 19.
6. Repeating Y during the same second round is rejected, with the canonical fingerprint unchanged.

All results are assertions in `tests/attack_training_fingerprint_tests.cpp`; **these are host tests, not screenshot-proven second-round gameplay in NeXium**. The native battle code, enemy AI, demo NRO and the Stage42–46 guest evidence remain unchanged. Do not claim the new round is guest-verified until a separate screenshot-gated route exists.

The scenario uses original placeholder units in a ROM-free homebrew; it is **not** Sega Saturn tactical content.
