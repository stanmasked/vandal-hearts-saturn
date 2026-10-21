# Stage53 — side-effect-free attack preview (ROM-free)

## Purpose

Stage50 ([real NeXium Victory #39502774414](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39502774414)) and Stage52 ([real NeXium Defeat #39557444750](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39557444750)) both completed green. Their entire combat hashes and image-based proofs are immutable acceptance baselines. Stage53 is a narrow gameplay-engine extension toward a tactics UI, not a claim about the original Saturn rules.

A new, **read-only** `Battle::preview_attack(attacker_id, defender_id) const` returns an `AttackPreview` with:
- `legal`: exactly the same action-validity rules as the actual attack; no attacks from the wrong side of the turn, duplicate actions, dead units, friendly fire, outside range or after Victory/Defeat;
- `damage`: actual HP lost (clamped to remaining defender HP; no overkill or negative HP);
- `remaining_hp`: projected defender HP after a hit, including the existing height advantage and one-point minimum damage;
- `ends_battle`: whether that hit would eliminate the final living unit on the defender's side. Killing one of **two** living enemies must not falsely declare Victory.

Invalid forecasts are `{false,0,0,false}`; reading a forecast can never change units, phase, round, selection or `battle_fingerprint`. The actual `Battle::attack` now **calls the same forecast** to enforce parity and then applies its projected HP once, marks the attacker acted and computes the resulting phase. No new enum values, fields in `Unit`, serialized state, keyboard inputs or framebuffer overlays were added. In particular, the existing Stage50/52 guest screenshots and all old golden fingerprints are expected to stay identical.

## Native automated acceptance

`tests/attack_preview_tests.cpp` is the independent CTest `attack_preview_contract`, automatically run on both GCC and Clang. The test exercises:

1. Four real ROM-free duel attacks, each forecast repeated 20 times with byte-identical battle fingerprint, then compared to the actual committed damage and all **seven pinned** Stage50 intermediate Victory hashes.
2. Illegal enemy out-of-phase, self-attack, unknown attacker and defender; duplicate attack after acting; terminal Victory or Defeat forecasts all fail without mutation.
3. Original four-unit 2v2 scene: one enemy slain without ending battle; second enemy slain by another ally triggers Victory; wrong attacker is prohibited from attacking again.
4. Advantage when attacking downhill (+2), minimum 1 damage when defense overpowers attack, ranged attack at distance 2, illegal melee hit beyond distance 1, overkill HP clamping.
5. Unmodified Stage52 eight-unopposed-attack Defeat checksum `3b0411b006f113c1` and irreversible terminal lock.

## Honest limitations and next step

This changes the native rules engine, and must not be called verified until new host CI passes *and* existing Stage50 and Stage52 independent NeXium guest runs remain green. The preview API is not yet displayed in the SDL tactical UI; that would require new UI design and real visual regression evidence. No original Sega Saturn assets or executable are used.
